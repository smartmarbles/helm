"""Owner-lease lock + optimistic-concurrency primitives (spec015 Task 2.4).

This module layers the spec §5.3 concurrency discipline on top of the external
:class:`RuntimeStoreAdapter` (Task 2.2). The adapter's generic, allowlisted
:meth:`RuntimeStoreAdapter.update` is the single write primitive; every
operation here is a read-then-allowlisted-update built on it. Single-writer
serialization per ``(session_id, workflow_id)`` is enforced by the owner lease
itself — the revision compare-and-swap is defense-in-depth layered on that
lease, not a substitute for it.

The two lock-loss failure modes are kept strictly distinct (plan Watch Out #6,
spec §5.3 Rules 5 and 6):

* **Rule 5 — pre-write reject** (:meth:`LockManager.compare_and_swap`): a
  mutation request carrying a stale ``expected_revision`` or arriving without a
  valid owner lease is refused *before* any mutation begins, raising
  :class:`StaleRevisionError` or :class:`LockNotHeldError`.
* **Rule 6 — mid-operation expiry** (:meth:`LockManager.assert_lease_live`): a
  lease the caller already holds expires *between acquire and complete*, raising
  :class:`LockExpiredError` to signal the correction path. Rule 6 triggers when
  ``current_time > lock.acquired_at + ttl``.

Idempotency dedupe is two-layered (spec §5.3 Rule 4, plan Watch Out #16):

* **Layer 1 — durable double-commit guard (authoritative, survives restart).**
  :meth:`LockManager.compare_and_swap` threads the request's ``operation_id``
  into the adapter mutation, which writes a ``mutation_audit`` row inside the
  SAME transaction as the workflow ``UPDATE``. The partial ``UNIQUE`` index on
  ``mutation_audit.operation_id`` rejects a second commit of the same
  ``operation_id`` — even one replayed by the host after a controller crash and
  restart — because the guard lives in SQLite/WAL. The duplicate is surfaced as
  :class:`DuplicateMutationError` and mapped to an idempotent no-op return.
* **Layer 2 — in-process lease-scoped cache (latency optimization ONLY).** While
  the SAME process holds a lease, a repeated request carrying the same
  :func:`idempotency_key` may be short-circuited from the ``_decisions`` cache,
  keyed by lock token. This cache is discarded on lease release AND on process
  restart; it carries NO crash-recovery guarantee and MUST NOT be relied on for
  correctness across a crash.
"""

from __future__ import annotations

import hashlib
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping

from helm_controller.config import ControllerConfig
from helm_controller.store.adapter import (
    DuplicateMutationError,
    MutationAudit,
    RecordNotFoundError,
    RuntimeStoreAdapter,
    RuntimeStoreRecord,
)
from helm_controller.store.errors import (
    LockConflictError,
    LockExpiredError,
    LockNotHeldError,
    StaleRevisionError,
)
from helm_controller.store.identity import RuntimeIdentity

DEFAULT_LOCK_TTL_SECONDS = 1800

_ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def idempotency_key(
    session_id: str,
    workflow_id: str,
    turn_id: str,
    hook_event: str,
    tool_use_id: str | None = None,
) -> str:
    """Derive the per-request idempotency key (spec §5.3 Rule 4).

    The key is ``sha256(f"{session_id}:{workflow_id}:{turn_id}:{hook_event}:
    {tool_use_id or ''}").hexdigest()[:32]``.
    """
    raw = f"{session_id}:{workflow_id}:{turn_id}:{hook_event}:{tool_use_id or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def new_lock_token() -> str:
    """Generate a fresh owner-lease ``lock_token`` (spec §3.4).

    This is the ONLY lock-token generation path; minting tokens inline is
    forbidden by §3.4. A grep assertion in ``test_identity.py`` enforces it.
    """
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime(_ISO_FORMAT)


def _parse_iso(value: str) -> datetime:
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


@dataclass(frozen=True)
class LockLease:
    """A held owner lease over a ``(session_id, workflow_id)`` workflow."""

    identity: RuntimeIdentity
    owner_agent: str
    lock_token: str
    acquired_at: datetime
    expires_at: datetime

    def is_expired(self, now: datetime) -> bool:
        """Rule 6 predicate: ``now > acquired_at + ttl`` (== ``now > expires_at``)."""
        return now > self.expires_at


class LockManager:
    """Owner-lease lock and optimistic-concurrency operations over the store."""

    def __init__(
        self,
        adapter: RuntimeStoreAdapter,
        config: ControllerConfig,
        *,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._adapter = adapter
        self._ttl_seconds = config.locking.lock_ttl_seconds
        self._clock = clock
        self._decisions: dict[str, dict[str, Any]] = {}
        self._decisions_guard = threading.Lock()

    @property
    def ttl_seconds(self) -> int:
        return self._ttl_seconds

    def acquire(self, identity: RuntimeIdentity, owner_agent: str) -> LockLease:
        """Acquire the owner lease for ``identity`` on behalf of ``owner_agent``.

        Re-acquiring an own, still-live lease is idempotent. A live lease held by
        a different owner raises :class:`LockConflictError`.
        """
        record = self._require_record(identity)
        now = self._clock()
        lock = record.row.owner_lock
        if (
            lock.active is not None
            and lock.expires_at is not None
            and lock.acquired_at is not None
            and lock.lock_token is not None
            and now <= _parse_iso(lock.expires_at)
        ):
            if lock.active == owner_agent:
                return LockLease(
                    identity=identity,
                    owner_agent=owner_agent,
                    lock_token=lock.lock_token,
                    acquired_at=_parse_iso(lock.acquired_at),
                    expires_at=_parse_iso(lock.expires_at),
                )
            raise LockConflictError(identity, lock.active)

        token = new_lock_token()
        acquired_at = now
        expires_at = now + timedelta(seconds=self._ttl_seconds)
        revision = record.row.audit.revision
        self._adapter.update(
            identity,
            workflow_fields={
                "owner_lock_active": owner_agent,
                "owner_lock_token": token,
                "owner_lock_acquired_at": _to_iso(acquired_at),
                "owner_lock_expires_at": _to_iso(expires_at),
                "revision": revision + 1,
            },
        )
        with self._decisions_guard:
            self._decisions[token] = {}
        return LockLease(
            identity=identity,
            owner_agent=owner_agent,
            lock_token=token,
            acquired_at=acquired_at,
            expires_at=expires_at,
        )

    def release(self, lease: LockLease) -> RuntimeStoreRecord:
        """Release ``lease`` and clear the owner-lock fields on the workflow."""
        record = self._require_record(lease.identity)
        lock = record.row.owner_lock
        if lock.lock_token != lease.lock_token:
            raise LockNotHeldError(
                lease.identity, "lease token does not match the active owner lock"
            )
        revision = record.row.audit.revision
        updated = self._adapter.update(
            lease.identity,
            workflow_fields={
                "owner_lock_active": None,
                "owner_lock_token": None,
                "owner_lock_acquired_at": None,
                "owner_lock_expires_at": None,
                "revision": revision + 1,
            },
        )
        with self._decisions_guard:
            self._decisions.pop(lease.lock_token, None)
        return updated

    def compare_and_swap(
        self,
        lease: LockLease,
        expected_revision: int,
        *,
        operation_id: str | None = None,
        operation: str = "compare_and_swap",
        workflow_fields: Mapping[str, Any] | None = None,
        row_fields: Mapping[str, Any] | None = None,
    ) -> RuntimeStoreRecord:
        """Apply an allowlisted mutation under a Rule 5 pre-write legality check.

        Rejects — before any mutation begins — on stale revision
        (:class:`StaleRevisionError`) or absent/expired owner lease
        (:class:`LockNotHeldError`). On success, writes the supplied fields with
        ``revision`` advanced to ``expected_revision + 1`` and an atomic
        ``mutation_audit`` row (durable double-commit guard, layer 1). When
        ``operation_id`` collides with an already-committed mutation — a retried
        hook, including one replayed after a controller restart — the adapter
        raises :class:`DuplicateMutationError`; this method maps it to an
        idempotent no-op, returning the current (already-committed) record
        WITHOUT re-applying the mutation.
        """
        record = self._require_record(lease.identity)
        self._reject_pre_write(record, lease, expected_revision, self._clock())
        workflow_updates = dict(workflow_fields or {})
        workflow_updates["revision"] = expected_revision + 1
        audit = MutationAudit(
            actor=lease.owner_agent,
            operation=operation,
            operation_id=operation_id,
            from_revision=expected_revision,
            to_revision=expected_revision + 1,
        )
        try:
            return self._adapter.update(
                lease.identity,
                workflow_fields=workflow_updates,
                row_fields=row_fields,
                audit=audit,
            )
        except DuplicateMutationError:
            return self._require_record(lease.identity)

    def assert_lease_live(self, lease: LockLease) -> None:
        """Rule 6 correction guard for a lease that may have expired mid-operation.

        Raises :class:`LockExpiredError` when ``now > acquired_at + ttl``. This is
        distinct from the Rule 5 pre-write rejects: it signals that an in-flight
        operation lost its lease and the caller must enter the correction path
        (reacquire within policy or terminalize), NOT that a fresh request was
        refused.
        """
        now = self._clock()
        if lease.is_expired(now):
            raise LockExpiredError(
                lease.identity, lease.lock_token, _to_iso(lease.expires_at)
            )

    def remembered_decision(self, lease: LockLease, key: str) -> Any | None:
        """Return the decision cached under ``key`` for this lease, if any.

        Layer-2 optimization only (plan Watch Out #16): this cache is
        process-local and lease-scoped — discarded on release and on process
        restart. It is NOT a crash-recovery guard; durable double-commit
        prevention is the ``operation_id`` UNIQUE index in
        :meth:`compare_and_swap`.
        """
        with self._decisions_guard:
            return self._decisions.get(lease.lock_token, {}).get(key)

    def remember_decision(self, lease: LockLease, key: str, decision: Any) -> None:
        """Cache ``decision`` under ``key`` for the duration of this lease.

        Layer-2 optimization only: process-local, discarded on release and on
        restart. MUST NOT be relied on for correctness across a crash.
        """
        with self._decisions_guard:
            self._decisions.setdefault(lease.lock_token, {})[key] = decision

    def _require_record(self, identity: RuntimeIdentity) -> RuntimeStoreRecord:
        record = self._adapter.read(identity)
        if record is None:
            raise RecordNotFoundError(identity)
        return record

    @staticmethod
    def _reject_pre_write(
        record: RuntimeStoreRecord,
        lease: LockLease,
        expected_revision: int,
        now: datetime,
    ) -> None:
        actual = record.row.audit.revision
        if actual != expected_revision:
            raise StaleRevisionError(lease.identity, expected_revision, actual)
        lock = record.row.owner_lock
        if lock.active is None or lock.lock_token != lease.lock_token:
            raise LockNotHeldError(
                lease.identity, "no active owner lease matching the caller"
            )
        if lock.expires_at is None or now > _parse_iso(lock.expires_at):
            raise LockNotHeldError(lease.identity, "owner lease has expired")
