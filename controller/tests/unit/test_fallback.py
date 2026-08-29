"""Tests for the session-memory fallback runtime store (spec015 Task 2.3)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import pytest

from helm_controller.config import ControllerConfig
from helm_controller.store.adapter import (
    RUNTIME_STORE_MODE_FALLBACK,
    RecordNotFoundError,
    RuntimeStoreAdapter,
    StoreError,
    TerminalMutationError,
    UnknownColumnError,
)
from helm_controller.store.fallback import (
    STORE_TIMEOUT_MS,
    SessionMemoryFallbackStore,
    _initial_columns,
    _is_lock_stale,
    _reject_unknown,
)
from helm_controller.store.identity import RuntimeIdentity

_IDENT = RuntimeIdentity("sess-1", "wf-1", "turn-1")
_IDENT_2 = RuntimeIdentity("sess-1", "wf-2", "turn-1")


def _store() -> SessionMemoryFallbackStore:
    return SessionMemoryFallbackStore()


def _seed(store: SessionMemoryFallbackStore, identity: RuntimeIdentity = _IDENT):
    return store.create(
        identity,
        row_id="BBR-000001",
        item_id="item-1",
        fsm_state_ref="ST-001",
        created_by="tester",
        immutable_fields_hash="hash-1",
    )


# --------------------------------------------------------------------------- #
# downgrade marker + round-trip
# --------------------------------------------------------------------------- #
def test_create_carries_fallback_downgrade_marker() -> None:
    store = _store()
    created = _seed(store)
    assert created.runtime_store_mode == RUNTIME_STORE_MODE_FALLBACK
    assert store.runtime_store_mode == RUNTIME_STORE_MODE_FALLBACK
    assert created.row.row_id == "BBR-000001"


def test_read_missing_returns_none() -> None:
    store = _store()
    assert store.read(_IDENT) is None


def test_read_skips_validation_when_disabled() -> None:
    store = _store()
    _seed(store)
    record = store.read(_IDENT, validate_contract=False)
    assert record is not None


def test_initialize_is_noop() -> None:
    store = _store()
    assert store.initialize() is None


def test_create_duplicate_identity_rejected() -> None:
    store = _store()
    _seed(store)
    with pytest.raises(StoreError, match="already exists"):
        _seed(store)


def test_create_vanished_record_raises(monkeypatch) -> None:
    store = _store()
    monkeypatch.setattr(store, "read", lambda *a, **k: None)
    with pytest.raises(StoreError, match="vanished after create"):
        _seed(store)


def test_from_config_uses_configured_timeout() -> None:
    config = ControllerConfig()
    store = SessionMemoryFallbackStore.from_config(config)
    assert store.store_timeout_ms == config.store.fallback_timeout_ms


def test_default_store_timeout_constant() -> None:
    store = _store()
    assert store.store_timeout_ms == STORE_TIMEOUT_MS


# --------------------------------------------------------------------------- #
# timeout trigger
# --------------------------------------------------------------------------- #
def test_exceeds_timeout_true_and_false() -> None:
    store = SessionMemoryFallbackStore(store_timeout_ms=100)
    assert store.exceeds_timeout(150.0) is True
    assert store.exceeds_timeout(50.0) is False


# --------------------------------------------------------------------------- #
# update: allowlist, terminal, missing, vanished
# --------------------------------------------------------------------------- #
def test_update_workflow_and_row_fields() -> None:
    store = _store()
    _seed(store)
    updated = store.update(
        _IDENT,
        workflow_fields={"fsm_state_ref": "ST-002"},
        row_fields={"lifecycle_stage": "route"},
    )
    assert updated.row.fsm_state_ref == "ST-002"
    assert updated.row.lifecycle_stage == "route"


def test_update_requires_at_least_one_field() -> None:
    store = _store()
    _seed(store)
    with pytest.raises(StoreError, match="at least one field"):
        store.update(_IDENT)


def test_update_rejects_unknown_workflow_column() -> None:
    store = _store()
    _seed(store)
    with pytest.raises(UnknownColumnError):
        store.update(_IDENT, workflow_fields={"nope": 1})


def test_update_rejects_unknown_row_column() -> None:
    store = _store()
    _seed(store)
    with pytest.raises(UnknownColumnError):
        store.update(_IDENT, row_fields={"nope": 1})


def test_update_missing_record_raises() -> None:
    store = _store()
    with pytest.raises(RecordNotFoundError):
        store.update(_IDENT, workflow_fields={"fsm_state_ref": "ST-002"})


def test_update_terminal_record_rejected() -> None:
    store = _store()
    _seed(store)
    store.update(
        _IDENT,
        workflow_fields={"is_terminal": 1, "workflow_lifecycle": "terminal"},
    )
    with pytest.raises(TerminalMutationError):
        store.update(_IDENT, workflow_fields={"fsm_state_ref": "ST-002"})


def test_update_vanished_record_raises(monkeypatch) -> None:
    store = _store()
    _seed(store)
    monkeypatch.setattr(store, "read", lambda *a, **k: None)
    with pytest.raises(StoreError, match="vanished after update"):
        store.update(_IDENT, workflow_fields={"fsm_state_ref": "ST-002"})


def test_serialize_reflects_active_owner_lock() -> None:
    store = _store()
    _seed(store)
    store.update(
        _IDENT,
        workflow_fields={
            "owner_lock_active": "AGENT_A",
            "owner_lock_token": "tok-1",
            "owner_lock_acquired_at": "2026-05-31T12:00:00Z",
            "owner_lock_expires_at": "2026-05-31T13:00:00Z",
        },
    )
    record = store.read(_IDENT)
    assert record is not None
    assert record.row.owner_lock.active == "AGENT_A"
    assert record.row.owner_lock.active_lock_count == 1


# --------------------------------------------------------------------------- #
# reconcile recovery
# --------------------------------------------------------------------------- #
def test_reconcile_terminalizes_active_and_discards_state(tmp_path: Path) -> None:
    store = _store()
    _seed(store, _IDENT)
    _seed(store, _IDENT_2)
    # Terminalize one workflow so reconcile only acts on the still-active one.
    store.update(
        _IDENT_2,
        workflow_fields={"is_terminal": 1, "workflow_lifecycle": "terminal"},
    )

    external = RuntimeStoreAdapter(tmp_path / "store.db")
    result = store.reconcile(external)

    assert result.terminalized == (_IDENT,)
    assert len(result.audit_trail) == 1
    assert result.audit_trail[0].boundary_event == "terminalize"
    # Live state discarded after recovery.
    assert store.read(_IDENT) is None
    assert store.read(_IDENT_2) is None
    # Audit trail survives recovery.
    assert len(store.audit_trail) == 1


def test_reconcile_with_no_active_workflows(tmp_path: Path) -> None:
    store = _store()
    external = RuntimeStoreAdapter(tmp_path / "store.db")
    result = store.reconcile(external)
    assert result.terminalized == ()
    assert result.audit_trail == ()


def test_reconcile_logs_via_injected_logger(tmp_path: Path) -> None:
    logger = logging.getLogger("test.fallback.recovery")
    store = SessionMemoryFallbackStore(logger=logger)
    _seed(store)
    external = RuntimeStoreAdapter(tmp_path / "store.db")
    result = store.reconcile(external)
    assert result.terminalized == (_IDENT,)


# --------------------------------------------------------------------------- #
# module-level helpers
# --------------------------------------------------------------------------- #
def test_initial_columns_defaults_all_gates_not_evaluated() -> None:
    columns = _initial_columns(
        _IDENT,
        row_id="BBR-000001",
        item_id="item-1",
        fsm_state_ref="ST-001",
        created_by="tester",
        immutable_fields_hash="hash-1",
        lifecycle_stage="intake",
        workflow_lifecycle="non_terminal_active",
        created_at="2026-05-31T12:00:00Z",
    )
    assert columns["revision"] == 1
    assert columns["is_terminal"] == 0
    assert columns["gate_bg_001"] == "not_evaluated"
    assert columns["gate_bg_006"] == "not_evaluated"


def test_reject_unknown_passes_for_allowed_column() -> None:
    _reject_unknown({"fsm_state_ref": "ST-002"}, frozenset({"fsm_state_ref"}), "t")


def test_reject_unknown_raises_for_disallowed_column() -> None:
    with pytest.raises(UnknownColumnError):
        _reject_unknown({"bad": 1}, frozenset({"fsm_state_ref"}), "t")


def test_is_lock_stale_inactive() -> None:
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    assert _is_lock_stale(None, "2026-05-31T11:00:00Z", now) is False


def test_is_lock_stale_no_expiry() -> None:
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    assert _is_lock_stale("AGENT_A", None, now) is False


def test_is_lock_stale_unparseable() -> None:
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    assert _is_lock_stale("AGENT_A", "garbage", now) is False


def test_is_lock_stale_expired() -> None:
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    assert _is_lock_stale("AGENT_A", "2026-05-31T11:00:00Z", now) is True


def test_is_lock_stale_live() -> None:
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    assert _is_lock_stale("AGENT_A", "2026-05-31T13:00:00Z", now) is False
