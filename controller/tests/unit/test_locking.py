"""Tests for owner-lease lock + optimistic-concurrency primitives (Task 2.4)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from helm_controller.config import ControllerConfig
from helm_controller.store.adapter import RuntimeStoreAdapter
from helm_controller.store.errors import (
    LockConflictError,
    LockExpiredError,
    LockNotHeldError,
    StaleRevisionError,
)
from helm_controller.store.identity import RuntimeIdentity, new_workflow_id
from helm_controller.store.locking import (
    DEFAULT_LOCK_TTL_SECONDS,
    LockLease,
    LockManager,
    RecordNotFoundError,
    _parse_iso,
    _to_iso,
    idempotency_key,
)

_IDENT = RuntimeIdentity("sess-1", "wf-1", "turn-1")


class _FakeClock:
    def __init__(self, start: datetime) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: int) -> None:
        self.now = self.now + timedelta(seconds=seconds)


def _setup(tmp_path: Path, identity: RuntimeIdentity = _IDENT):
    clock = _FakeClock(datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc))
    adapter = RuntimeStoreAdapter(tmp_path / "store.db")
    config = ControllerConfig()
    manager = LockManager(adapter, config, clock=clock)
    adapter.create(
        identity,
        row_id="BBR-000001",
        item_id="item-1",
        fsm_state_ref="ST-001",
        created_by="tester",
        immutable_fields_hash="hash-1",
    )
    return adapter, manager, clock, config


# --------------------------------------------------------------------------- #
# acquire / release
# --------------------------------------------------------------------------- #
def test_acquire_release_round_trip(tmp_path: Path) -> None:
    adapter, manager, _clock, _config = _setup(tmp_path)
    lease = manager.acquire(_IDENT, "AGENT_A")
    assert lease.owner_agent == "AGENT_A"

    held = adapter.read(_IDENT)
    assert held is not None
    assert held.row.owner_lock.active == "AGENT_A"
    assert held.row.owner_lock.lock_token == lease.lock_token

    released = manager.release(lease)
    assert released.row.owner_lock.active is None
    assert released.row.owner_lock.lock_token is None


def test_ttl_seconds_sourced_from_config(tmp_path: Path) -> None:
    _adapter, manager, _clock, config = _setup(tmp_path)
    assert manager.ttl_seconds == config.locking.lock_ttl_seconds
    assert config.locking.lock_ttl_seconds == DEFAULT_LOCK_TTL_SECONDS


def test_reacquire_same_owner_is_idempotent(tmp_path: Path) -> None:
    _adapter, manager, _clock, _config = _setup(tmp_path)
    first = manager.acquire(_IDENT, "AGENT_A")
    second = manager.acquire(_IDENT, "AGENT_A")
    assert first.lock_token == second.lock_token


def test_acquire_conflict_with_live_lease(tmp_path: Path) -> None:
    _adapter, manager, _clock, _config = _setup(tmp_path)
    manager.acquire(_IDENT, "AGENT_A")
    with pytest.raises(LockConflictError) as exc:
        manager.acquire(_IDENT, "AGENT_B")
    assert exc.value.current_owner == "AGENT_A"


def test_acquire_remints_after_expiry(tmp_path: Path) -> None:
    _adapter, manager, clock, config = _setup(tmp_path)
    first = manager.acquire(_IDENT, "AGENT_A")
    clock.advance(config.locking.lock_ttl_seconds + 1)
    second = manager.acquire(_IDENT, "AGENT_B")
    assert second.lock_token != first.lock_token
    assert second.owner_agent == "AGENT_B"


def test_acquire_missing_record_raises(tmp_path: Path) -> None:
    _adapter, manager, _clock, _config = _setup(tmp_path)
    missing = RuntimeIdentity("sess-1", new_workflow_id(), "turn-1")
    with pytest.raises(RecordNotFoundError):
        manager.acquire(missing, "AGENT_A")


def test_release_with_stale_token_rejected(tmp_path: Path) -> None:
    _adapter, manager, _clock, _config = _setup(tmp_path)
    lease = manager.acquire(_IDENT, "AGENT_A")
    manager.release(lease)
    with pytest.raises(LockNotHeldError):
        manager.release(lease)


# --------------------------------------------------------------------------- #
# compare_and_swap — Rule 5 pre-write rejects + success
# --------------------------------------------------------------------------- #
def test_compare_and_swap_success(tmp_path: Path) -> None:
    adapter, manager, _clock, _config = _setup(tmp_path)
    lease = manager.acquire(_IDENT, "AGENT_A")
    base = adapter.read(_IDENT).row.audit.revision
    result = manager.compare_and_swap(
        lease, base, workflow_fields={"fsm_state_ref": "ST-002"}
    )
    assert result.row.fsm_state_ref == "ST-002"
    assert result.row.audit.revision == base + 1


def test_compare_and_swap_stale_revision(tmp_path: Path) -> None:
    adapter, manager, _clock, _config = _setup(tmp_path)
    lease = manager.acquire(_IDENT, "AGENT_A")
    base = adapter.read(_IDENT).row.audit.revision
    with pytest.raises(StaleRevisionError) as exc:
        manager.compare_and_swap(
            lease, base + 99, workflow_fields={"fsm_state_ref": "ST-002"}
        )
    assert exc.value.expected_revision == base + 99
    assert exc.value.actual_revision == base


def test_compare_and_swap_no_active_lease(tmp_path: Path) -> None:
    adapter, manager, _clock, _config = _setup(tmp_path)
    lease = manager.acquire(_IDENT, "AGENT_A")
    manager.release(lease)
    base = adapter.read(_IDENT).row.audit.revision
    with pytest.raises(LockNotHeldError, match="no active owner lease"):
        manager.compare_and_swap(
            lease, base, workflow_fields={"fsm_state_ref": "ST-002"}
        )


def test_compare_and_swap_token_mismatch(tmp_path: Path) -> None:
    adapter, manager, _clock, _config = _setup(tmp_path)
    lease = manager.acquire(_IDENT, "AGENT_A")
    # A different live token occupies the lock; the caller's lease no longer wins.
    adapter.update(_IDENT, workflow_fields={"owner_lock_token": "other-token"})
    base = adapter.read(_IDENT).row.audit.revision
    with pytest.raises(LockNotHeldError, match="no active owner lease"):
        manager.compare_and_swap(
            lease, base, workflow_fields={"fsm_state_ref": "ST-002"}
        )


def test_compare_and_swap_null_expiry_rejected(tmp_path: Path) -> None:
    adapter, manager, _clock, _config = _setup(tmp_path)
    lease = manager.acquire(_IDENT, "AGENT_A")
    adapter.update(_IDENT, workflow_fields={"owner_lock_expires_at": None})
    base = adapter.read(_IDENT).row.audit.revision
    with pytest.raises(LockNotHeldError, match="owner lease has expired"):
        manager.compare_and_swap(
            lease, base, workflow_fields={"fsm_state_ref": "ST-002"}
        )


def test_compare_and_swap_expired_by_time_rejected(tmp_path: Path) -> None:
    adapter, manager, clock, config = _setup(tmp_path)
    lease = manager.acquire(_IDENT, "AGENT_A")
    base = adapter.read(_IDENT).row.audit.revision
    clock.advance(config.locking.lock_ttl_seconds + 1)
    with pytest.raises(LockNotHeldError, match="owner lease has expired"):
        manager.compare_and_swap(
            lease, base, workflow_fields={"fsm_state_ref": "ST-002"}
        )


def test_compare_and_swap_missing_record_raises(tmp_path: Path) -> None:
    _adapter, manager, _clock, _config = _setup(tmp_path)
    missing_ident = RuntimeIdentity("sess-1", new_workflow_id(), "turn-1")
    lease = LockLease(
        identity=missing_ident,
        owner_agent="AGENT_A",
        lock_token="tok",
        acquired_at=datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc),
        expires_at=datetime(2026, 5, 31, 12, 30, tzinfo=timezone.utc),
    )
    with pytest.raises(RecordNotFoundError):
        manager.compare_and_swap(lease, 1, workflow_fields={"fsm_state_ref": "ST-002"})


# --------------------------------------------------------------------------- #
# Rule 6 — mid-operation expiry
# --------------------------------------------------------------------------- #
def test_assert_lease_live_passes_when_unexpired(tmp_path: Path) -> None:
    _adapter, manager, _clock, _config = _setup(tmp_path)
    lease = manager.acquire(_IDENT, "AGENT_A")
    manager.assert_lease_live(lease)  # no raise


def test_assert_lease_live_raises_after_expiry(tmp_path: Path) -> None:
    _adapter, manager, clock, config = _setup(tmp_path)
    lease = manager.acquire(_IDENT, "AGENT_A")
    clock.advance(config.locking.lock_ttl_seconds + 1)
    with pytest.raises(LockExpiredError) as exc:
        manager.assert_lease_live(lease)
    assert exc.value.lock_token == lease.lock_token


def test_lock_lease_is_expired_predicate() -> None:
    acquired = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    expires = datetime(2026, 5, 31, 12, 30, tzinfo=timezone.utc)
    lease = LockLease(_IDENT, "AGENT_A", "tok", acquired, expires)
    assert lease.is_expired(datetime(2026, 5, 31, 13, 0, tzinfo=timezone.utc)) is True
    assert lease.is_expired(datetime(2026, 5, 31, 12, 15, tzinfo=timezone.utc)) is False


# --------------------------------------------------------------------------- #
# idempotency dedupe — layer 1 (durable) + layer 2 (in-process)
# --------------------------------------------------------------------------- #
def test_idempotency_key_with_and_without_tool_use_id() -> None:
    with_tool = idempotency_key("s", "w", "t", "PreToolUse", "tu-1")
    without_tool = idempotency_key("s", "w", "t", "PreToolUse")
    again = idempotency_key("s", "w", "t", "PreToolUse", "tu-1")
    assert with_tool != without_tool
    assert with_tool == again
    assert len(with_tool) == 32


def test_durable_dedupe_same_process_no_op(tmp_path: Path) -> None:
    adapter, manager, _clock, _config = _setup(tmp_path)
    lease = manager.acquire(_IDENT, "AGENT_A")
    base = adapter.read(_IDENT).row.audit.revision
    op = idempotency_key("sess-1", "wf-1", "turn-1", "PreToolUse", "tu-1")

    first = manager.compare_and_swap(
        lease, base, operation_id=op, workflow_fields={"fsm_state_ref": "ST-002"}
    )
    assert first.row.audit.revision == base + 1

    # A retry within the same process replays the same operation_id: idempotent
    # no-op returning the already-committed record without re-mutating.
    retry = manager.compare_and_swap(
        lease,
        first.row.audit.revision,
        operation_id=op,
        workflow_fields={"fsm_state_ref": "ST-009"},
    )
    assert retry.row.audit.revision == first.row.audit.revision
    assert retry.row.fsm_state_ref == "ST-002"


def test_durable_dedupe_restart_simulation(tmp_path: Path) -> None:
    db_path = tmp_path / "store.db"
    adapter1 = RuntimeStoreAdapter(db_path)
    config = ControllerConfig()
    manager1 = LockManager(adapter1, config)
    adapter1.create(
        _IDENT,
        row_id="BBR-000001",
        item_id="item-1",
        fsm_state_ref="ST-001",
        created_by="tester",
        immutable_fields_hash="hash-1",
    )
    lease = manager1.acquire(_IDENT, "AGENT_A")
    base = adapter1.read(_IDENT).row.audit.revision
    op = idempotency_key("sess-1", "wf-1", "turn-1", "PreToolUse", "tu-1")

    committed = manager1.compare_and_swap(
        lease, base, operation_id=op, workflow_fields={"fsm_state_ref": "ST-002"}
    )
    assert committed.row.audit.revision == base + 1

    # Simulate a controller restart: brand-new adapter + manager over the same
    # database file, then the host replays the already-committed operation_id.
    adapter2 = RuntimeStoreAdapter(db_path)
    manager2 = LockManager(adapter2, config)
    lease2 = manager2.acquire(_IDENT, "AGENT_A")
    restart_base = adapter2.read(_IDENT).row.audit.revision
    replay = manager2.compare_and_swap(
        lease2,
        restart_base,
        operation_id=op,
        workflow_fields={"fsm_state_ref": "ST-009"},
    )
    # Idempotent no-op: revision unchanged, original value preserved.
    assert replay.row.audit.revision == restart_base
    assert replay.row.fsm_state_ref == "ST-002"

    # Exactly one durable audit row for the replayed operation_id.
    conn = sqlite3.connect(db_path)
    try:
        replayed = conn.execute(
            "SELECT count(*) FROM mutation_audit WHERE operation_id = ?", (op,)
        ).fetchone()[0]
    finally:
        conn.close()
    assert replayed == 1

    # A fresh operation_id still commits normally, advancing revision once.
    op2 = idempotency_key("sess-1", "wf-1", "turn-2", "PreToolUse", "tu-2")
    advanced = manager2.compare_and_swap(
        lease2,
        restart_base,
        operation_id=op2,
        workflow_fields={"fsm_state_ref": "ST-004"},
    )
    assert advanced.row.audit.revision == restart_base + 1


def test_in_process_decision_cache_layer_two(tmp_path: Path) -> None:
    _adapter, manager, _clock, _config = _setup(tmp_path)
    lease = manager.acquire(_IDENT, "AGENT_A")
    op = idempotency_key("sess-1", "wf-1", "turn-1", "PreToolUse", "tu-1")

    # Unknown key short-circuits to None.
    assert manager.remembered_decision(lease, op) is None

    manager.remember_decision(lease, op, {"decision": "allow"})
    assert manager.remembered_decision(lease, op) == {"decision": "allow"}

    # A second key under the same lease reuses the existing cache bucket.
    manager.remember_decision(lease, "other", {"decision": "deny"})
    assert manager.remembered_decision(lease, "other") == {"decision": "deny"}

    # The cache is lease-scoped: released leases lose their decisions.
    manager.release(lease)
    assert manager.remembered_decision(lease, op) is None


# --------------------------------------------------------------------------- #
# private helpers: _parse_iso / _to_iso
# --------------------------------------------------------------------------- #
def test_locking_parse_iso_zulu() -> None:
    assert _parse_iso("2026-05-31T12:00:00Z") == datetime(
        2026, 5, 31, 12, 0, tzinfo=timezone.utc
    )


def test_locking_parse_iso_offset() -> None:
    assert _parse_iso("2026-05-31T12:00:00+00:00") == datetime(
        2026, 5, 31, 12, 0, tzinfo=timezone.utc
    )


def test_locking_parse_iso_naive_assumes_utc() -> None:
    assert _parse_iso("2026-05-31T12:00:00") == datetime(
        2026, 5, 31, 12, 0, tzinfo=timezone.utc
    )


def test_locking_to_iso_round_trips() -> None:
    moment = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    assert _to_iso(moment) == "2026-05-31T12:00:00Z"
    assert _parse_iso(_to_iso(moment)) == moment
