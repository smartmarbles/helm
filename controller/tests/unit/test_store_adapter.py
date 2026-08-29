"""Tests for the external SQLite runtime-store adapter (spec015 Task 2.2/2.4)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from helm_controller.config import ControllerConfig
from helm_controller.contracts import validator as validator_module
from helm_controller.contracts.validator import ContractValidationError, Contract
from helm_controller.store import adapter as adapter_module
from helm_controller.store.adapter import (
    DuplicateMutationError,
    MutationAudit,
    RecordNotFoundError,
    RUNTIME_STORE_MODE_EXTERNAL,
    RuntimeStoreAdapter,
    StoreError,
    TerminalMutationError,
    UnknownColumnError,
    _parse_iso,
)
from helm_controller.store.identity import RuntimeIdentity

_is_lock_stale = RuntimeStoreAdapter._is_lock_stale

_IDENT = RuntimeIdentity("sess-1", "wf-1", "turn-1")


def _new_adapter(tmp_path: Path) -> RuntimeStoreAdapter:
    return RuntimeStoreAdapter(tmp_path / "store.db")


def _seed(adapter: RuntimeStoreAdapter, identity: RuntimeIdentity = _IDENT):
    return adapter.create(
        identity,
        row_id="BBR-000001",
        item_id="item-1",
        fsm_state_ref="ST-001",
        created_by="tester",
        immutable_fields_hash="hash-1",
    )


# --------------------------------------------------------------------------- #
# create / read round-trip
# --------------------------------------------------------------------------- #
def test_create_then_read_round_trip(tmp_path: Path) -> None:
    adapter = _new_adapter(tmp_path)
    created = _seed(adapter)
    assert created.runtime_store_mode == RUNTIME_STORE_MODE_EXTERNAL
    assert created.row.row_id == "BBR-000001"
    assert created.row.audit.revision == 1
    assert created.row.owner_lock.active is None
    assert created.row.owner_lock.active_lock_count == 0

    fetched = adapter.read(_IDENT)
    assert fetched is not None
    assert fetched.identity == _IDENT
    assert fetched.row.item_id == "item-1"


def test_read_missing_identity_returns_none(tmp_path: Path) -> None:
    adapter = _new_adapter(tmp_path)
    assert adapter.read(_IDENT) is None


def test_read_skips_contract_validation_when_disabled(tmp_path: Path, monkeypatch) -> None:
    adapter = _new_adapter(tmp_path)
    _seed(adapter)

    def _boom(*_args, **_kwargs):  # pragma: no cover - must not be called
        raise AssertionError("validate should not run when disabled")

    monkeypatch.setattr(adapter_module, "validate", _boom)
    record = adapter.read(_IDENT, validate_contract=False)
    assert record is not None


def test_read_contract_validation_failure_wraps_store_error(
    tmp_path: Path, monkeypatch
) -> None:
    adapter = _new_adapter(tmp_path)
    _seed(adapter)

    def _raise(*_args, **_kwargs):
        raise ContractValidationError(Contract.BLACKBOARD, ["forced failure"])

    monkeypatch.setattr(adapter_module, "validate", _raise)
    with pytest.raises(StoreError, match="failed contract validation"):
        adapter.read(_IDENT)


def test_create_vanished_record_raises(tmp_path: Path, monkeypatch) -> None:
    adapter = _new_adapter(tmp_path)
    monkeypatch.setattr(adapter, "read", lambda *a, **k: None)
    with pytest.raises(StoreError, match="vanished after create"):
        _seed(adapter)


def test_from_config_builds_adapter(tmp_path: Path) -> None:
    config = ControllerConfig()
    adapter = RuntimeStoreAdapter.from_config(tmp_path, config)
    _seed(adapter)
    assert (tmp_path / config.store.db_path).is_file()


# --------------------------------------------------------------------------- #
# update: allowlist, terminal immutability, missing record
# --------------------------------------------------------------------------- #
def test_update_workflow_and_row_fields(tmp_path: Path) -> None:
    adapter = _new_adapter(tmp_path)
    _seed(adapter)
    updated = adapter.update(
        _IDENT,
        workflow_fields={"fsm_state_ref": "ST-002"},
        row_fields={"lifecycle_stage": "route"},
    )
    assert updated.row.fsm_state_ref == "ST-002"
    assert updated.row.lifecycle_stage == "route"


def test_update_row_fields_only(tmp_path: Path) -> None:
    adapter = _new_adapter(tmp_path)
    _seed(adapter)
    updated = adapter.update(_IDENT, row_fields={"lifecycle_stage": "route"})
    assert updated.row.lifecycle_stage == "route"


def test_update_requires_at_least_one_field(tmp_path: Path) -> None:
    adapter = _new_adapter(tmp_path)
    _seed(adapter)
    with pytest.raises(StoreError, match="at least one field"):
        adapter.update(_IDENT)


def test_update_rejects_unknown_workflow_column(tmp_path: Path) -> None:
    adapter = _new_adapter(tmp_path)
    _seed(adapter)
    with pytest.raises(UnknownColumnError) as exc:
        adapter.update(_IDENT, workflow_fields={"not_a_column": 1})
    assert exc.value.table == "workflows"
    assert exc.value.column == "not_a_column"


def test_update_rejects_unknown_row_column(tmp_path: Path) -> None:
    adapter = _new_adapter(tmp_path)
    _seed(adapter)
    with pytest.raises(UnknownColumnError) as exc:
        adapter.update(_IDENT, row_fields={"bogus": 1})
    assert exc.value.table == "blackboard_rows"


def test_update_missing_record_raises(tmp_path: Path) -> None:
    adapter = _new_adapter(tmp_path)
    with pytest.raises(RecordNotFoundError) as exc:
        adapter.update(_IDENT, workflow_fields={"fsm_state_ref": "ST-002"})
    assert exc.value.identity == _IDENT


def test_update_terminal_record_rejected(tmp_path: Path) -> None:
    adapter = _new_adapter(tmp_path)
    _seed(adapter)
    adapter.update(
        _IDENT,
        workflow_fields={"is_terminal": 1, "workflow_lifecycle": "terminal"},
    )
    terminal = adapter.read(_IDENT)
    assert terminal is not None
    assert terminal.row.terminal.is_terminal is True
    with pytest.raises(TerminalMutationError) as exc:
        adapter.update(_IDENT, workflow_fields={"fsm_state_ref": "ST-002"})
    assert exc.value.identity == _IDENT


def test_update_vanished_record_raises(tmp_path: Path, monkeypatch) -> None:
    adapter = _new_adapter(tmp_path)
    _seed(adapter)
    monkeypatch.setattr(adapter, "read", lambda *a, **k: None)
    with pytest.raises(StoreError, match="vanished after update"):
        adapter.update(_IDENT, workflow_fields={"fsm_state_ref": "ST-002"})


# --------------------------------------------------------------------------- #
# mutation_audit / durable double-commit guard
# --------------------------------------------------------------------------- #
def test_update_with_audit_writes_single_row(tmp_path: Path) -> None:
    db_path = tmp_path / "store.db"
    adapter = RuntimeStoreAdapter(db_path)
    _seed(adapter)
    audit = MutationAudit(
        actor="AGENT_A",
        operation="compare_and_swap",
        operation_id="op-1",
        from_revision=1,
        to_revision=2,
    )
    adapter.update(_IDENT, workflow_fields={"revision": 2}, audit=audit)

    conn = sqlite3.connect(db_path)
    try:
        count = conn.execute(
            "SELECT count(*) FROM mutation_audit WHERE operation_id = 'op-1'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert count == 1


def test_duplicate_operation_id_raises_duplicate_mutation(tmp_path: Path) -> None:
    adapter = _new_adapter(tmp_path)
    _seed(adapter)
    audit = MutationAudit(actor="AGENT_A", operation="cas", operation_id="op-dup")
    adapter.update(_IDENT, workflow_fields={"revision": 2}, audit=audit)
    with pytest.raises(DuplicateMutationError) as exc:
        adapter.update(_IDENT, workflow_fields={"revision": 3}, audit=audit)
    assert exc.value.operation_id == "op-dup"
    assert exc.value.identity == _IDENT


def test_audit_integrity_error_without_operation_id_reraises(tmp_path: Path) -> None:
    adapter = _new_adapter(tmp_path)
    _seed(adapter)
    # actor is NOT NULL in the schema; a None actor with no operation_id forces a
    # bare IntegrityError that the guard must re-raise rather than mask.
    bad_audit = MutationAudit(actor=None, operation="cas", operation_id=None)  # type: ignore[arg-type]
    with pytest.raises(sqlite3.IntegrityError):
        adapter.update(_IDENT, workflow_fields={"revision": 2}, audit=bad_audit)


# --------------------------------------------------------------------------- #
# migrations idempotency
# --------------------------------------------------------------------------- #
def test_initialize_is_idempotent(tmp_path: Path) -> None:
    adapter = _new_adapter(tmp_path)
    # Constructor already applied 0001; a second call must skip the applied one.
    adapter.initialize()
    _seed(adapter)
    assert adapter.read(_IDENT) is not None


# --------------------------------------------------------------------------- #
# error class constructors
# --------------------------------------------------------------------------- #
def test_store_error_subclass_messages() -> None:
    assert "no workflow record" in str(RecordNotFoundError(_IDENT))
    assert "terminal and immutable" in str(TerminalMutationError(_IDENT))
    assert "not a mutable column" in str(UnknownColumnError("workflows", "x"))
    dup = DuplicateMutationError(_IDENT, "op-9")
    assert dup.operation_id == "op-9"
    assert "already committed" in str(dup)


# --------------------------------------------------------------------------- #
# private helpers: _parse_iso / _is_lock_stale
# --------------------------------------------------------------------------- #
def test_parse_iso_zulu_suffix() -> None:
    parsed = _parse_iso("2026-05-31T12:00:00Z")
    assert parsed == datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)


def test_parse_iso_explicit_offset() -> None:
    parsed = _parse_iso("2026-05-31T12:00:00+00:00")
    assert parsed == datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)


def test_parse_iso_naive_gets_utc() -> None:
    parsed = _parse_iso("2026-05-31T12:00:00")
    assert parsed == datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)


def test_parse_iso_invalid_returns_none() -> None:
    assert _parse_iso("not-a-timestamp") is None


def test_is_lock_stale_inactive_lock() -> None:
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    assert _is_lock_stale(None, "2026-05-31T11:00:00Z", now) is False


def test_is_lock_stale_no_expiry() -> None:
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    assert _is_lock_stale("AGENT_A", None, now) is False


def test_is_lock_stale_unparseable_expiry() -> None:
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    assert _is_lock_stale("AGENT_A", "garbage", now) is False


def test_is_lock_stale_expired() -> None:
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    assert _is_lock_stale("AGENT_A", "2026-05-31T11:00:00Z", now) is True


def test_is_lock_stale_live() -> None:
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    assert _is_lock_stale("AGENT_A", "2026-05-31T13:00:00Z", now) is False
