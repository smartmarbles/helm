"""Session-memory fallback runtime-store adapter (spec015 Task 2.3).

This adapter is the ``session_memory_fallback`` runtime-store mode (spec §5.2):
an interim, in-process holding tier used only when the ``external`` SQLite store
(:mod:`helm_controller.store.adapter`) is unavailable. It mirrors the public
interface of :class:`~helm_controller.store.adapter.RuntimeStoreAdapter`
(``initialize`` / ``read`` / ``create`` / ``update``) so the controller can swap
tiers without changing call sites, and every record it surfaces carries the
explicit downgrade marker
:data:`~helm_controller.store.adapter.RUNTIME_STORE_MODE_FALLBACK` so downstream
evaluators can tell a degraded record from an authoritative one.

**Trigger conditions** (decided by the controller, thresholds owned here):
fallback activates when (1) the SQLite database file is absent or unreadable at
controller startup, or (2) any external store operation exceeds
:data:`STORE_TIMEOUT_MS` (default 100 ms, configurable via ``helm-controller.toml``
``[store] fallback_timeout_ms``; see :meth:`SessionMemoryFallbackStore.from_config`).

**Thread safety (mandatory):** ``http.server.ThreadingHTTPServer`` (Task 3.0)
dispatches concurrent hook requests on separate threads. Two simultaneous hook
events would race on the in-process state dict and silently corrupt workflow
state, so the dict is guarded by a :class:`threading.Lock` and every
read-modify-write sequence runs inside a ``with self._lock:`` block.

**Recovery semantics (mandatory):** when the external store returns,
:meth:`SessionMemoryFallbackStore.reconcile` does **not** merge in-memory state
into the store — that would risk store corruption from partially-applied
in-memory turns. Instead it emits a ``terminalize`` boundary event for every
active fallback workflow (preserving the fallback audit trail in-memory only),
discards the live fallback state, and logs the recovery. The caller then resets
controller state to initial-IDLE from the now-authoritative external store.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from helm_controller.config import ControllerConfig
from helm_controller.contracts.blackboard import (
    Audit,
    BlackboardRow,
    OwnerLock,
    Terminal,
)
from helm_controller.store.adapter import (
    RUNTIME_STORE_MODE_FALLBACK,
    RecordNotFoundError,
    RuntimeStoreAdapter,
    RuntimeStoreRecord,
    StoreError,
    TerminalMutationError,
    UnknownColumnError,
    _GATE_COLUMNS,
    _ROW_MUTABLE_COLUMNS,
    _WORKFLOW_MUTABLE_COLUMNS,
    _parse_iso,
)
from helm_controller.store.identity import RuntimeIdentity

STORE_TIMEOUT_MS = 100

_LOGGER = logging.getLogger("helm_controller.store.fallback")

_TERMINALIZE = "terminalize"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class FallbackAuditEvent:
    """An in-memory audit marker for a fallback-mode lifecycle event."""

    identity: RuntimeIdentity
    boundary_event: str
    occurred_at: str
    detail: str


@dataclass(frozen=True)
class ReconciliationResult:
    """Outcome of an external-store recovery reconciliation pass."""

    terminalized: tuple[RuntimeIdentity, ...]
    audit_trail: tuple[FallbackAuditEvent, ...]


class SessionMemoryFallbackStore:
    """In-process interim runtime store, addressed by composite identity.

    Mirrors the public surface of
    :class:`~helm_controller.store.adapter.RuntimeStoreAdapter`. State lives in a
    single dict of flat column maps guarded by :attr:`_lock`; records are
    serialized into the same :class:`~helm_controller.contracts.blackboard.BlackboardRow`
    contract the external adapter emits, tagged with the fallback downgrade marker.
    """

    runtime_store_mode = RUNTIME_STORE_MODE_FALLBACK

    def __init__(
        self,
        *,
        store_timeout_ms: int = STORE_TIMEOUT_MS,
        clock: Callable[[], datetime] = _utcnow,
        logger: logging.Logger | None = None,
    ) -> None:
        self._records: dict[RuntimeIdentity, dict[str, Any]] = {}
        self._audit_trail: list[FallbackAuditEvent] = []
        self._lock = threading.Lock()
        self._clock = clock
        self._log = logger or _LOGGER
        self.store_timeout_ms = store_timeout_ms

    @classmethod
    def from_config(
        cls,
        config: ControllerConfig,
        *,
        clock: Callable[[], datetime] = _utcnow,
        logger: logging.Logger | None = None,
    ) -> "SessionMemoryFallbackStore":
        return cls(
            store_timeout_ms=config.store.fallback_timeout_ms,
            clock=clock,
            logger=logger,
        )

    def exceeds_timeout(self, elapsed_ms: float) -> bool:
        """Return whether an external store op latency warrants fallback (trigger 2)."""
        return elapsed_ms > self.store_timeout_ms

    def initialize(self) -> None:
        """No-op: the fallback tier holds no durable schema. Interface parity only."""

    def read(
        self,
        identity: RuntimeIdentity,
        *,
        validate_contract: bool = True,
    ) -> RuntimeStoreRecord | None:
        """Serialize the in-process record for ``identity`` with the downgrade marker."""
        now = self._clock()
        with self._lock:
            columns = self._records.get(identity)
            row = None if columns is None else self._serialize(dict(columns), now)
        if row is None:
            return None
        if validate_contract:
            RuntimeStoreAdapter._validate(row)
        return RuntimeStoreRecord(
            runtime_store_mode=self.runtime_store_mode,
            identity=identity,
            row=row,
        )

    def create(
        self,
        identity: RuntimeIdentity,
        *,
        row_id: str,
        item_id: str,
        fsm_state_ref: str,
        created_by: str,
        immutable_fields_hash: str,
        lifecycle_stage: str = "intake",
        workflow_lifecycle: str = "non_terminal_active",
        created_at: str | None = None,
    ) -> RuntimeStoreRecord:
        """Insert a new fallback record. Rejects a duplicate composite identity."""
        timestamp = created_at or self._now_iso()
        columns = _initial_columns(
            identity,
            row_id=row_id,
            item_id=item_id,
            fsm_state_ref=fsm_state_ref,
            created_by=created_by,
            immutable_fields_hash=immutable_fields_hash,
            lifecycle_stage=lifecycle_stage,
            workflow_lifecycle=workflow_lifecycle,
            created_at=timestamp,
        )
        with self._lock:
            if identity in self._records:
                raise StoreError(f"fallback record for {identity!r} already exists")
            self._records[identity] = columns
        created = self.read(identity)
        if created is None:
            raise StoreError(f"record for {identity!r} vanished after create")
        return created

    def update(
        self,
        identity: RuntimeIdentity,
        *,
        workflow_fields: Mapping[str, Any] | None = None,
        row_fields: Mapping[str, Any] | None = None,
    ) -> RuntimeStoreRecord:
        """Mutate allowlisted columns under the lock. Rejects terminal records."""
        workflow_updates = dict(workflow_fields or {})
        row_updates = dict(row_fields or {})
        if not workflow_updates and not row_updates:
            raise StoreError("update requires at least one field to mutate")
        _reject_unknown(workflow_updates, _WORKFLOW_MUTABLE_COLUMNS, "workflows")
        _reject_unknown(row_updates, _ROW_MUTABLE_COLUMNS, "blackboard_rows")
        with self._lock:
            columns = self._records.get(identity)
            if columns is None:
                raise RecordNotFoundError(identity)
            if columns["is_terminal"] == 1:
                raise TerminalMutationError(identity)
            columns.update(workflow_updates)
            columns.update(row_updates)
        updated = self.read(identity)
        if updated is None:
            raise StoreError(f"record for {identity!r} vanished after update")
        return updated

    def reconcile(self, external_store: RuntimeStoreAdapter) -> ReconciliationResult:
        """Recover to the external store WITHOUT merging in-memory state.

        Emits a ``terminalize`` audit event for every active (non-terminal)
        fallback workflow, preserves the fallback audit trail in-memory, then
        discards the live fallback state. The caller resets controller state to
        initial-IDLE from ``external_store`` after this returns.
        """
        with self._lock:
            active = [
                identity
                for identity, columns in self._records.items()
                if columns["is_terminal"] != 1
            ]
            for identity in active:
                event = FallbackAuditEvent(
                    identity=identity,
                    boundary_event=_TERMINALIZE,
                    occurred_at=self._now_iso(),
                    detail="terminalized on external-store recovery (no merge)",
                )
                self._audit_trail.append(event)
                self._log.warning(
                    "fallback recovery: terminalizing active workflow %r", identity
                )
            terminalized = tuple(active)
            audit_trail = tuple(self._audit_trail)
            self._records.clear()
        self._log.info(
            "external store %r available; fallback state discarded after recovery",
            external_store,
        )
        return ReconciliationResult(
            terminalized=terminalized,
            audit_trail=audit_trail,
        )

    @property
    def audit_trail(self) -> tuple[FallbackAuditEvent, ...]:
        """A snapshot of the in-memory fallback audit trail (survives recovery)."""
        with self._lock:
            return tuple(self._audit_trail)

    def _serialize(self, columns: Mapping[str, Any], now: datetime) -> BlackboardRow:
        owner_active = columns["owner_lock_active"]
        return BlackboardRow(
            row_present=True,
            row_schema_valid=True,
            row_id=columns["row_id"],
            session_id=columns["session_id"],
            workflow_id=columns["workflow_id"],
            predecessor_workflow_id=columns["predecessor_workflow_id"],
            successor_workflow_id=columns["successor_workflow_id"],
            item_id=columns["item_id"],
            lifecycle_stage=columns["lifecycle_stage"],
            workflow_lifecycle=columns["workflow_lifecycle"],
            fsm_state_ref=columns["fsm_state_ref"],
            prior_non_terminal_fsm_state=columns["prior_non_terminal_fsm_state"],
            owner_lock=OwnerLock(
                active=owner_active,
                lock_token=columns["owner_lock_token"],
                acquired_at=columns["owner_lock_acquired_at"],
                expires_at=columns["owner_lock_expires_at"],
                is_stale=_is_lock_stale(
                    owner_active, columns["owner_lock_expires_at"], now
                ),
                active_lock_count=1 if owner_active is not None else 0,
            ),
            gates={
                gate_id: columns[column]
                for gate_id, column in _GATE_COLUMNS.items()
            },
            required_gates_passed=bool(columns["required_gates_passed"]),
            terminal=Terminal(
                is_terminal=bool(columns["is_terminal"]),
                terminal_state=columns["terminal_state"],
                terminalized_at=columns["terminalized_at"],
                terminal_reason=columns["terminal_reason"],
            ),
            audit=Audit(
                created_at=columns["created_at"],
                created_by=columns["created_by"],
                revision=columns["revision"],
                immutable_fields_hash=columns["immutable_fields_hash"],
                audit_fields_mutated=bool(columns["audit_fields_mutated"]),
            ),
            mutation_attempt_keys=[],
        )

    def _now_iso(self) -> str:
        return self._clock().strftime("%Y-%m-%dT%H:%M:%SZ")


def _initial_columns(
    identity: RuntimeIdentity,
    *,
    row_id: str,
    item_id: str,
    fsm_state_ref: str,
    created_by: str,
    immutable_fields_hash: str,
    lifecycle_stage: str,
    workflow_lifecycle: str,
    created_at: str,
) -> dict[str, Any]:
    """Build a flat column map mirroring the external store's create defaults."""
    columns: dict[str, Any] = {
        "session_id": identity.session_id,
        "workflow_id": identity.workflow_id,
        "workflow_lifecycle": workflow_lifecycle,
        "fsm_state_ref": fsm_state_ref,
        "prior_non_terminal_fsm_state": None,
        "predecessor_workflow_id": None,
        "successor_workflow_id": None,
        "owner_lock_active": None,
        "owner_lock_token": None,
        "owner_lock_acquired_at": None,
        "owner_lock_expires_at": None,
        "revision": 1,
        "is_terminal": 0,
        "terminal_state": None,
        "terminalized_at": None,
        "terminal_reason": None,
        "row_id": row_id,
        "item_id": item_id,
        "lifecycle_stage": lifecycle_stage,
        "required_gates_passed": 0,
        "created_at": created_at,
        "created_by": created_by,
        "immutable_fields_hash": immutable_fields_hash,
        "audit_fields_mutated": 0,
    }
    for column in _GATE_COLUMNS.values():
        columns[column] = "not_evaluated"
    return columns


def _reject_unknown(
    fields: Mapping[str, Any], allowed: frozenset[str], table: str
) -> None:
    for column in fields:
        if column not in allowed:
            raise UnknownColumnError(table, column)


def _is_lock_stale(
    active: str | None, expires_at: str | None, now: datetime
) -> bool:
    if active is None or expires_at is None:
        return False
    parsed = _parse_iso(expires_at)
    if parsed is None:
        return False
    return now >= parsed
