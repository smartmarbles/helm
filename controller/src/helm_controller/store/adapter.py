"""External runtime-store adapter (spec015 Task 2.2).

This adapter is the ``external`` runtime-store mode (spec §5.1): the SQLite
database is the operational source of truth. The ``session_memory_fallback``
mode is a separate adapter (Task 2.3); both surface records carrying an
explicit :data:`RuntimeStoreRecord.runtime_store_mode` marker so downstream
evaluators can tell which tier produced a record.

Thread-safety choice — **pattern (a): connection-per-request.**
``http.server.ThreadingHTTPServer`` (Task 3.0) dispatches every hook request on
a fresh thread, and ``sqlite3`` raises ``ProgrammingError`` if a connection
created on one thread is touched from another. This adapter opens a brand-new
connection for every public operation (via :meth:`_connect`) and closes it
before returning, so no connection ever crosses a thread boundary. Pattern (a)
is chosen over pattern (b) (one ``check_same_thread=False`` connection behind a
``threading.Lock``) because SQLite connection setup is negligibly cheap, the
per-request connection needs no shared lock and therefore serializes nothing,
and WAL mode already permits concurrent readers alongside a single writer. No
shared mutable connection state exists for a stray thread to corrupt.

Every connection sets ``PRAGMA journal_mode=WAL``, ``PRAGMA busy_timeout``, and
``PRAGMA foreign_keys=ON`` on open (spec015 Task 2.1 / Watch Out #15). The
migration scripts intentionally omit ``journal_mode`` because it cannot run
inside a transaction; the adapter owns it at connection-open time.

The flat blackboard-row contract is serialized by JOINing ``blackboard_rows``
with ``workflows`` (Task 2.1 design note / Watch Out #7): workflow-scoped
persistent fields (linkage, owner lock, revision, terminal metadata,
``prior_non_terminal_fsm_state``) live only on ``workflows`` and are joined in at
read time rather than duplicated.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from helm_controller.config import ControllerConfig
from helm_controller.contracts.blackboard import (
    Audit,
    BlackboardRow,
    OwnerLock,
    Terminal,
)
from helm_controller.contracts.validator import (
    Contract,
    ContractValidationError,
    validate,
)
from helm_controller.store.identity import RuntimeIdentity

RUNTIME_STORE_MODE_EXTERNAL = "external"
RUNTIME_STORE_MODE_FALLBACK = "session_memory_fallback"

_GATE_COLUMNS: dict[str, str] = {
    "BG-001": "gate_bg_001",
    "BG-002": "gate_bg_002",
    "BG-003": "gate_bg_003",
    "BG-004": "gate_bg_004",
    "BG-005": "gate_bg_005",
    "BG-006": "gate_bg_006",
}

_WORKFLOW_MUTABLE_COLUMNS: frozenset[str] = frozenset(
    {
        "workflow_lifecycle",
        "fsm_state_ref",
        "prior_non_terminal_fsm_state",
        "predecessor_workflow_id",
        "successor_workflow_id",
        "owner_lock_active",
        "owner_lock_token",
        "owner_lock_acquired_at",
        "owner_lock_expires_at",
        "revision",
        "boundary_event",
        "is_terminal",
        "terminal_state",
        "terminalized_at",
        "terminal_reason",
    }
)

_ROW_MUTABLE_COLUMNS: frozenset[str] = frozenset(
    {
        "item_id",
        "lifecycle_stage",
        "gate_bg_001",
        "gate_bg_002",
        "gate_bg_003",
        "gate_bg_004",
        "gate_bg_005",
        "gate_bg_006",
        "gate_first_failure_id",
        "required_gates_passed",
        "immutable_fields_hash",
        "audit_fields_mutated",
    }
)

_READ_JOIN_SQL = """
SELECT
    w.session_id                    AS session_id,
    w.workflow_id                   AS workflow_id,
    w.workflow_lifecycle            AS workflow_lifecycle,
    w.fsm_state_ref                 AS fsm_state_ref,
    w.prior_non_terminal_fsm_state  AS prior_non_terminal_fsm_state,
    w.predecessor_workflow_id       AS predecessor_workflow_id,
    w.successor_workflow_id         AS successor_workflow_id,
    w.owner_lock_active             AS owner_lock_active,
    w.owner_lock_token              AS owner_lock_token,
    w.owner_lock_acquired_at        AS owner_lock_acquired_at,
    w.owner_lock_expires_at         AS owner_lock_expires_at,
    w.revision                      AS revision,
    w.is_terminal                   AS is_terminal,
    w.terminal_state                AS terminal_state,
    w.terminalized_at               AS terminalized_at,
    w.terminal_reason               AS terminal_reason,
    b.row_id                        AS row_id,
    b.item_id                       AS item_id,
    b.lifecycle_stage               AS lifecycle_stage,
    b.gate_bg_001                   AS gate_bg_001,
    b.gate_bg_002                   AS gate_bg_002,
    b.gate_bg_003                   AS gate_bg_003,
    b.gate_bg_004                   AS gate_bg_004,
    b.gate_bg_005                   AS gate_bg_005,
    b.gate_bg_006                   AS gate_bg_006,
    b.required_gates_passed         AS required_gates_passed,
    b.created_at                    AS created_at,
    b.created_by                    AS created_by,
    b.immutable_fields_hash         AS immutable_fields_hash,
    b.audit_fields_mutated          AS audit_fields_mutated
FROM workflows AS w
JOIN blackboard_rows AS b
    ON b.session_id = w.session_id
   AND b.workflow_id = w.workflow_id
WHERE w.session_id = ? AND w.workflow_id = ?
"""


class StoreError(Exception):
    """Base class for runtime-store adapter failures."""


class RecordNotFoundError(StoreError):
    """Raised when a mutation targets an identity with no workflow record."""

    def __init__(self, identity: RuntimeIdentity) -> None:
        self.identity = identity
        super().__init__(f"no workflow record for {identity!r}")


class TerminalMutationError(StoreError):
    """Raised when a mutation targets a workflow whose terminal row is immutable."""

    def __init__(self, identity: RuntimeIdentity) -> None:
        self.identity = identity
        super().__init__(f"workflow {identity!r} is terminal and immutable")


class UnknownColumnError(StoreError):
    """Raised when a mutation names a column outside the mutable allowlist."""

    def __init__(self, table: str, column: str) -> None:
        self.table = table
        self.column = column
        super().__init__(f"{column!r} is not a mutable column of {table!r}")


class DuplicateMutationError(StoreError):
    """Durable double-commit guard tripped (spec015 Task 2.4, layer 1).

    Raised when the ``mutation_audit`` insert that commits inside the same
    transaction as a workflow ``UPDATE`` collides with the partial ``UNIQUE``
    index on ``mutation_audit.operation_id``. Because the guard lives in
    SQLite/WAL, it rejects a retried operation carrying an already-committed
    ``operation_id`` even across a controller restart. The whole transaction is
    rolled back, so the second mutation is never applied; callers treat this as
    an idempotent no-op.
    """

    def __init__(self, identity: RuntimeIdentity, operation_id: str) -> None:
        self.identity = identity
        self.operation_id = operation_id
        super().__init__(
            f"operation_id {operation_id!r} already committed for {identity!r}"
        )


@dataclass(frozen=True)
class MutationAudit:
    """Audit-trail row written atomically with a workflow mutation (Task 2.4).

    ``operation_id`` is the durable idempotency key (spec §5.3 Rule 4); when it
    is non-null the partial ``UNIQUE`` index on ``mutation_audit.operation_id``
    enforces single-commit. ``from_revision`` / ``to_revision`` record the
    compare-and-swap revision delta the mutation applied.
    """

    actor: str
    operation: str
    operation_id: str | None = None
    from_revision: int | None = None
    to_revision: int | None = None
    correlation_id: str | None = None


@dataclass(frozen=True)
class RuntimeStoreRecord:
    """A serialized store record tagged with the tier that produced it."""

    runtime_store_mode: str
    identity: RuntimeIdentity
    row: BlackboardRow


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: str) -> datetime | None:
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


class RuntimeStoreAdapter:
    """SQLite-backed external runtime store, addressed by composite identity."""

    runtime_store_mode = RUNTIME_STORE_MODE_EXTERNAL

    def __init__(
        self,
        db_path: Path,
        *,
        busy_timeout_ms: int = 5000,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._db_path = db_path
        self._busy_timeout_ms = busy_timeout_ms
        self._clock = clock
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @classmethod
    def from_config(
        cls,
        workspace: Path,
        config: ControllerConfig,
        *,
        clock: Callable[[], datetime] = _utcnow,
    ) -> "RuntimeStoreAdapter":
        return cls(
            workspace / config.store.db_path,
            busy_timeout_ms=config.store.busy_timeout_ms,
            clock=clock,
        )

    def initialize(self) -> None:
        """Apply any unapplied migrations. Idempotent — safe to call repeatedly."""
        with self._connect() as conn:
            applied = self._applied_versions(conn)
            for path in self._migration_paths():
                if path.stem in applied:
                    continue
                conn.executescript(path.read_text(encoding="utf-8"))

    def read(
        self,
        identity: RuntimeIdentity,
        *,
        validate_contract: bool = True,
    ) -> RuntimeStoreRecord | None:
        """Serialize the workflow + blackboard row for ``identity`` via JOIN."""
        with self._connect() as conn:
            record = conn.execute(
                _READ_JOIN_SQL, (identity.session_id, identity.workflow_id)
            ).fetchone()
        if record is None:
            return None
        row = self._serialize(record, self._clock())
        if validate_contract:
            self._validate(row)
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
        """Insert the paired ``workflows`` + ``blackboard_rows`` record."""
        timestamp = created_at or self._now_iso()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO workflows "
                "(session_id, workflow_id, workflow_lifecycle, fsm_state_ref, "
                "created_at, created_by) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    identity.session_id,
                    identity.workflow_id,
                    workflow_lifecycle,
                    fsm_state_ref,
                    timestamp,
                    created_by,
                ),
            )
            conn.execute(
                "INSERT INTO blackboard_rows "
                "(row_id, session_id, workflow_id, item_id, lifecycle_stage, "
                "created_at, created_by, immutable_fields_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    row_id,
                    identity.session_id,
                    identity.workflow_id,
                    item_id,
                    lifecycle_stage,
                    timestamp,
                    created_by,
                    immutable_fields_hash,
                ),
            )
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
        audit: MutationAudit | None = None,
    ) -> RuntimeStoreRecord:
        """Mutate allowlisted columns. Rejects terminal (write-once) records.

        When ``audit`` is supplied, a ``mutation_audit`` row is inserted inside
        the SAME transaction as the workflow ``UPDATE`` (Task 2.4 durable
        double-commit guard): the ``UPDATE`` and the audit insert commit
        atomically, so a duplicate ``operation_id`` trips the partial ``UNIQUE``
        index and rolls back the entire mutation, raising
        :class:`DuplicateMutationError`.
        """
        workflow_updates = dict(workflow_fields or {})
        row_updates = dict(row_fields or {})
        if not workflow_updates and not row_updates:
            raise StoreError("update requires at least one field to mutate")
        self._reject_unknown(workflow_updates, _WORKFLOW_MUTABLE_COLUMNS, "workflows")
        self._reject_unknown(row_updates, _ROW_MUTABLE_COLUMNS, "blackboard_rows")
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT is_terminal FROM workflows "
                "WHERE session_id = ? AND workflow_id = ?",
                (identity.session_id, identity.workflow_id),
            ).fetchone()
            if existing is None:
                raise RecordNotFoundError(identity)
            if existing["is_terminal"] == 1:
                raise TerminalMutationError(identity)
            if workflow_updates:
                self._apply_update(conn, "workflows", workflow_updates, identity)
            if row_updates:
                self._apply_update(conn, "blackboard_rows", row_updates, identity)
            if audit is not None:
                self._insert_audit(conn, identity, audit)
        updated = self.read(identity)
        if updated is None:
            raise StoreError(f"record for {identity!r} vanished after update")
        return updated

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(
            self._db_path, timeout=self._busy_timeout_ms / 1000.0
        )
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(f"PRAGMA busy_timeout={self._busy_timeout_ms}")
            conn.execute("PRAGMA foreign_keys=ON")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _insert_audit(
        self,
        conn: sqlite3.Connection,
        identity: RuntimeIdentity,
        audit: MutationAudit,
    ) -> None:
        try:
            conn.execute(
                "INSERT INTO mutation_audit "
                "(session_id, workflow_id, actor, operation, operation_id, "
                "from_revision, to_revision, correlation_id, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    identity.session_id,
                    identity.workflow_id,
                    audit.actor,
                    audit.operation,
                    audit.operation_id,
                    audit.from_revision,
                    audit.to_revision,
                    audit.correlation_id,
                    self._now_iso(),
                ),
            )
        except sqlite3.IntegrityError as exc:
            if audit.operation_id is None:
                raise
            raise DuplicateMutationError(identity, audit.operation_id) from exc

    def _migration_paths(self) -> list[Path]:
        return sorted((Path(__file__).parent / "migrations").glob("*.sql"))

    @staticmethod
    def _applied_versions(conn: sqlite3.Connection) -> set[str]:
        try:
            rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
        except sqlite3.OperationalError:
            return set()
        return {row["version"] for row in rows}

    @staticmethod
    def _reject_unknown(
        fields: Mapping[str, Any], allowed: frozenset[str], table: str
    ) -> None:
        for column in fields:
            if column not in allowed:
                raise UnknownColumnError(table, column)

    @staticmethod
    def _apply_update(
        conn: sqlite3.Connection,
        table: str,
        fields: Mapping[str, Any],
        identity: RuntimeIdentity,
    ) -> None:
        assignments = ", ".join(f"{column} = ?" for column in fields)
        params = [*fields.values(), identity.session_id, identity.workflow_id]
        conn.execute(
            f"UPDATE {table} SET {assignments} "
            "WHERE session_id = ? AND workflow_id = ?",
            params,
        )

    def _serialize(self, record: sqlite3.Row, now: datetime) -> BlackboardRow:
        owner_active = record["owner_lock_active"]
        return BlackboardRow(
            row_present=True,
            row_schema_valid=True,
            row_id=record["row_id"],
            session_id=record["session_id"],
            workflow_id=record["workflow_id"],
            predecessor_workflow_id=record["predecessor_workflow_id"],
            successor_workflow_id=record["successor_workflow_id"],
            item_id=record["item_id"],
            lifecycle_stage=record["lifecycle_stage"],
            workflow_lifecycle=record["workflow_lifecycle"],
            fsm_state_ref=record["fsm_state_ref"],
            prior_non_terminal_fsm_state=record["prior_non_terminal_fsm_state"],
            owner_lock=OwnerLock(
                active=owner_active,
                lock_token=record["owner_lock_token"],
                acquired_at=record["owner_lock_acquired_at"],
                expires_at=record["owner_lock_expires_at"],
                is_stale=self._is_lock_stale(
                    owner_active, record["owner_lock_expires_at"], now
                ),
                active_lock_count=1 if owner_active is not None else 0,
            ),
            gates={
                gate_id: record[column]
                for gate_id, column in _GATE_COLUMNS.items()
            },
            required_gates_passed=bool(record["required_gates_passed"]),
            terminal=Terminal(
                is_terminal=bool(record["is_terminal"]),
                terminal_state=record["terminal_state"],
                terminalized_at=record["terminalized_at"],
                terminal_reason=record["terminal_reason"],
            ),
            audit=Audit(
                created_at=record["created_at"],
                created_by=record["created_by"],
                revision=record["revision"],
                immutable_fields_hash=record["immutable_fields_hash"],
                audit_fields_mutated=bool(record["audit_fields_mutated"]),
            ),
            mutation_attempt_keys=[],
        )

    @staticmethod
    def _is_lock_stale(
        active: str | None, expires_at: str | None, now: datetime
    ) -> bool:
        if active is None or expires_at is None:
            return False
        parsed = _parse_iso(expires_at)
        if parsed is None:
            return False
        return now >= parsed

    @staticmethod
    def _validate(row: BlackboardRow) -> None:
        try:
            validate(row.to_dict(), Contract.BLACKBOARD)
        except ContractValidationError as exc:
            raise StoreError(f"serialized row failed contract validation: {exc}") from exc

    def _now_iso(self) -> str:
        return self._clock().strftime("%Y-%m-%dT%H:%M:%SZ")
