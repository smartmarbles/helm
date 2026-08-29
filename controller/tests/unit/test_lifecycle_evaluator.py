"""Tests for the lifecycle boundary evaluator entry point (Task 7.5).

Exercises the §4.4 apply/deny paths through the real runtime-store write path:
`new` over empty/terminal/active/suspended sessions, `resume` from suspended vs
terminal, `supersede` linkage, `suspend`/`resume` prior-state round trip, and
`terminalize` boundary_event stamping.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from helm_controller.config import ControllerConfig
from helm_controller.lifecycle.evaluator import (
    BoundaryRequest,
    BoundaryRequestError,
    LifecycleBoundaryEvaluator,
    NewWorkflowSeed,
    SessionWorkflowState,
)
from helm_controller.lifecycle.legality import BoundaryEvent, SourceLifecycle
from helm_controller.store.adapter import RuntimeStoreAdapter
from helm_controller.store.identity import RuntimeIdentity
from helm_controller.store.locking import LockManager

SESSION = "sess-1"
TURN = "turn-1"
OWNER = "ARTHUR"


class _FakeClock:
    def __init__(self, start: datetime) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now


def _setup(tmp_path: Path):
    clock = _FakeClock(datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc))
    db_path = tmp_path / "store.db"
    adapter = RuntimeStoreAdapter(db_path)
    config = ControllerConfig()
    manager = LockManager(adapter, config, clock=clock)
    evaluator = LifecycleBoundaryEvaluator(adapter, manager, clock=clock)
    return adapter, manager, evaluator, clock, db_path


def _seed(row_id: str = "BBR-000001") -> NewWorkflowSeed:
    return NewWorkflowSeed(
        row_id=row_id,
        item_id="item",
        immutable_fields_hash="hash",
        initial_fsm_state="ST-080",
    )


def _create(
    adapter: RuntimeStoreAdapter,
    workflow_id: str,
    *,
    lifecycle: str = "non_terminal_active",
    fsm_state: str = "ST-080",
    row_id: str = "BBR-000001",
) -> RuntimeIdentity:
    identity = RuntimeIdentity(SESSION, workflow_id, TURN)
    adapter.create(
        identity,
        row_id=row_id,
        item_id="item",
        fsm_state_ref=fsm_state,
        created_by="tester",
        immutable_fields_hash="hash",
        workflow_lifecycle=lifecycle,
    )
    return identity


def _read_boundary_event(db_path: Path, workflow_id: str) -> str | None:
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT boundary_event FROM workflows "
            "WHERE session_id = ? AND workflow_id = ?",
            (SESSION, workflow_id),
        ).fetchone()
    finally:
        conn.close()
    return None if row is None else row["boundary_event"]


# --------------------------------------------------------------------------- #
# `new`
# --------------------------------------------------------------------------- #
def test_new_over_empty_session_is_applied(tmp_path: Path) -> None:
    adapter, _m, evaluator, _c, db_path = _setup(tmp_path)
    request = BoundaryRequest(
        event=BoundaryEvent.NEW,
        session_id=SESSION,
        turn_id=TURN,
        owner_agent=OWNER,
        new_seed=_seed(),
    )
    decision = evaluator.evaluate(request)
    assert decision.applied is True
    assert decision.legal is True
    assert decision.source is SourceLifecycle.NONE
    assert decision.boundary_event == "new"
    assert decision.workflow_id is not None

    record = adapter.read(RuntimeIdentity(SESSION, decision.workflow_id, TURN))
    assert record is not None
    assert record.row.workflow_lifecycle == "non_terminal_active"
    assert record.row.owner_lock.active == OWNER
    assert _read_boundary_event(db_path, decision.workflow_id) == "new"


def test_new_legal_even_when_terminal_workflow_present(tmp_path: Path) -> None:
    # A terminal workflow in the session does NOT block a `new` (source NONE):
    # terminal workflows never populate the active/suspended registry pointers.
    adapter, _m, evaluator, _c, _db = _setup(tmp_path)
    target = _create(adapter, "wf-terminal")
    evaluator.evaluate(
        BoundaryRequest(
            event=BoundaryEvent.TERMINALIZE,
            session_id=SESSION,
            turn_id=TURN,
            owner_agent=OWNER,
            target_workflow_id="wf-terminal",
            transition_id="TR-030",
        )
    )
    assert adapter.read(target).row.terminal.is_terminal is True

    decision = evaluator.evaluate(
        BoundaryRequest(
            event=BoundaryEvent.NEW,
            session_id=SESSION,
            turn_id=TURN,
            owner_agent=OWNER,
            new_seed=_seed(row_id="BBR-000002"),
        )
    )
    assert decision.applied is True
    assert decision.source is SourceLifecycle.NONE


def test_new_over_active_is_denied(tmp_path: Path) -> None:
    _a, _m, evaluator, _c, _db = _setup(tmp_path)
    decision = evaluator.evaluate(
        BoundaryRequest(
            event=BoundaryEvent.NEW,
            session_id=SESSION,
            turn_id=TURN,
            owner_agent=OWNER,
            session_state=SessionWorkflowState(active_workflow_id="wf-active"),
            new_seed=_seed(),
        )
    )
    assert decision.applied is False
    assert decision.legal is False
    assert decision.source is SourceLifecycle.NON_TERMINAL_ACTIVE


def test_new_over_suspended_is_denied_and_non_destructive(tmp_path: Path) -> None:
    # §4.5 ST-000 disambiguation: a suspended workflow in the registry forces
    # source = suspended → `new` illegal; the suspended workflow is untouched.
    adapter, _m, evaluator, _c, _db = _setup(tmp_path)
    suspended = _create(adapter, "wf-susp", lifecycle="non_terminal_suspended")

    decision = evaluator.evaluate(
        BoundaryRequest(
            event=BoundaryEvent.NEW,
            session_id=SESSION,
            turn_id=TURN,
            owner_agent=OWNER,
            session_state=SessionWorkflowState(suspended_workflow_ids=("wf-susp",)),
            new_seed=_seed(row_id="BBR-000002"),
        )
    )
    assert decision.applied is False
    assert decision.source is SourceLifecycle.NON_TERMINAL_SUSPENDED
    assert "silently discard" in decision.reason
    # Suspended workflow remains intact (not discarded, not mutated).
    still = adapter.read(suspended)
    assert still is not None
    assert still.row.workflow_lifecycle == "non_terminal_suspended"


def test_new_missing_seed_raises(tmp_path: Path) -> None:
    _a, _m, evaluator, _c, _db = _setup(tmp_path)
    with pytest.raises(BoundaryRequestError, match="requires new_seed"):
        evaluator.evaluate(
            BoundaryRequest(
                event=BoundaryEvent.NEW,
                session_id=SESSION,
                turn_id=TURN,
                owner_agent=OWNER,
            )
        )


# --------------------------------------------------------------------------- #
# `suspend` / `resume` round trip + prior_non_terminal_fsm_state
# --------------------------------------------------------------------------- #
def test_suspend_then_resume_round_trip(tmp_path: Path) -> None:
    adapter, manager, evaluator, _c, _db = _setup(tmp_path)
    identity = _create(adapter, "wf-1", fsm_state="ST-080")
    manager.acquire(identity, OWNER)

    suspend = evaluator.evaluate(
        BoundaryRequest(
            event=BoundaryEvent.SUSPEND,
            session_id=SESSION,
            turn_id=TURN,
            owner_agent=OWNER,
            target_workflow_id="wf-1",
        )
    )
    assert suspend.applied is True
    assert suspend.source is SourceLifecycle.NON_TERMINAL_ACTIVE
    assert suspend.boundary_event == "suspend"
    assert suspend.prior_non_terminal_fsm_state == "ST-080"

    suspended = adapter.read(identity)
    assert suspended.row.workflow_lifecycle == "non_terminal_suspended"
    assert suspended.row.owner_lock.active is None  # ownership cleared (§5.3 #2)
    assert suspended.row.prior_non_terminal_fsm_state == "ST-080"  # POL-014C write

    resume = evaluator.evaluate(
        BoundaryRequest(
            event=BoundaryEvent.RESUME,
            session_id=SESSION,
            turn_id=TURN,
            owner_agent=OWNER,
            target_workflow_id="wf-1",
        )
    )
    assert resume.applied is True
    assert resume.source is SourceLifecycle.NON_TERMINAL_SUSPENDED
    assert resume.boundary_event == "resume"
    assert resume.prior_non_terminal_fsm_state is None

    resumed = adapter.read(identity)
    assert resumed.row.workflow_lifecycle == "non_terminal_active"
    assert resumed.row.owner_lock.active == OWNER  # lock restored (§4.5 #2)
    assert resumed.row.prior_non_terminal_fsm_state is None  # POL-014C clear


def test_suspend_from_suspended_is_denied(tmp_path: Path) -> None:
    adapter, _m, evaluator, _c, _db = _setup(tmp_path)
    _create(adapter, "wf-susp", lifecycle="non_terminal_suspended")
    decision = evaluator.evaluate(
        BoundaryRequest(
            event=BoundaryEvent.SUSPEND,
            session_id=SESSION,
            turn_id=TURN,
            owner_agent=OWNER,
            target_workflow_id="wf-susp",
        )
    )
    assert decision.applied is False
    assert decision.source is SourceLifecycle.NON_TERMINAL_SUSPENDED


def test_resume_from_terminal_is_denied(tmp_path: Path) -> None:
    adapter, _m, evaluator, _c, _db = _setup(tmp_path)
    _create(adapter, "wf-1")
    evaluator.evaluate(
        BoundaryRequest(
            event=BoundaryEvent.TERMINALIZE,
            session_id=SESSION,
            turn_id=TURN,
            owner_agent=OWNER,
            target_workflow_id="wf-1",
            transition_id="TR-030",
        )
    )
    decision = evaluator.evaluate(
        BoundaryRequest(
            event=BoundaryEvent.RESUME,
            session_id=SESSION,
            turn_id=TURN,
            owner_agent=OWNER,
            target_workflow_id="wf-1",
        )
    )
    assert decision.applied is False
    assert decision.legal is False
    assert decision.source is SourceLifecycle.TERMINAL
    assert "immutable" in decision.reason


def test_resume_with_no_target_is_denied(tmp_path: Path) -> None:
    _a, _m, evaluator, _c, _db = _setup(tmp_path)
    decision = evaluator.evaluate(
        BoundaryRequest(
            event=BoundaryEvent.RESUME,
            session_id=SESSION,
            turn_id=TURN,
            owner_agent=OWNER,
            target_workflow_id=None,
        )
    )
    assert decision.applied is False
    assert decision.source is SourceLifecycle.NONE


def test_resume_with_unknown_target_is_denied(tmp_path: Path) -> None:
    # target supplied but absent from the store → source NONE → illegal.
    _a, _m, evaluator, _c, _db = _setup(tmp_path)
    decision = evaluator.evaluate(
        BoundaryRequest(
            event=BoundaryEvent.RESUME,
            session_id=SESSION,
            turn_id=TURN,
            owner_agent=OWNER,
            target_workflow_id="ghost",
        )
    )
    assert decision.applied is False
    assert decision.source is SourceLifecycle.NONE


# --------------------------------------------------------------------------- #
# `supersede`
# --------------------------------------------------------------------------- #
def test_supersede_active_links_predecessor_and_successor(tmp_path: Path) -> None:
    adapter, manager, evaluator, _c, _db = _setup(tmp_path)
    predecessor = _create(adapter, "wf-pred")
    manager.acquire(predecessor, OWNER)

    decision = evaluator.evaluate(
        BoundaryRequest(
            event=BoundaryEvent.SUPERSEDE,
            session_id=SESSION,
            turn_id=TURN,
            owner_agent=OWNER,
            target_workflow_id="wf-pred",
            new_seed=_seed(row_id="BBR-000002"),
        )
    )
    assert decision.applied is True
    assert decision.source is SourceLifecycle.NON_TERMINAL_ACTIVE
    assert decision.boundary_event == "supersede"
    successor_id = decision.workflow_id
    assert decision.predecessor_workflow_id == "wf-pred"

    pred_record = adapter.read(predecessor)
    assert pred_record.row.terminal.is_terminal is True
    assert pred_record.row.workflow_lifecycle == "terminal"
    assert pred_record.row.successor_workflow_id == successor_id
    assert pred_record.row.owner_lock.active is None  # predecessor lock cleared

    succ_record = adapter.read(RuntimeIdentity(SESSION, successor_id, TURN))
    assert succ_record.row.workflow_lifecycle == "non_terminal_active"
    assert succ_record.row.predecessor_workflow_id == "wf-pred"
    assert succ_record.row.owner_lock.active == OWNER


def test_supersede_suspended_predecessor_is_legal(tmp_path: Path) -> None:
    adapter, _m, evaluator, _c, _db = _setup(tmp_path)
    predecessor = _create(adapter, "wf-pred", lifecycle="non_terminal_suspended")
    decision = evaluator.evaluate(
        BoundaryRequest(
            event=BoundaryEvent.SUPERSEDE,
            session_id=SESSION,
            turn_id=TURN,
            owner_agent=OWNER,
            target_workflow_id="wf-pred",
            new_seed=_seed(row_id="BBR-000002"),
        )
    )
    assert decision.applied is True
    assert decision.source is SourceLifecycle.NON_TERMINAL_SUSPENDED
    pred_record = adapter.read(predecessor)
    assert pred_record.row.terminal.is_terminal is True
    assert pred_record.row.successor_workflow_id == decision.workflow_id


def test_supersede_from_terminal_is_denied(tmp_path: Path) -> None:
    adapter, _m, evaluator, _c, _db = _setup(tmp_path)
    _create(adapter, "wf-1")
    evaluator.evaluate(
        BoundaryRequest(
            event=BoundaryEvent.TERMINALIZE,
            session_id=SESSION,
            turn_id=TURN,
            owner_agent=OWNER,
            target_workflow_id="wf-1",
            transition_id="TR-030",
        )
    )
    decision = evaluator.evaluate(
        BoundaryRequest(
            event=BoundaryEvent.SUPERSEDE,
            session_id=SESSION,
            turn_id=TURN,
            owner_agent=OWNER,
            target_workflow_id="wf-1",
            new_seed=_seed(row_id="BBR-000002"),
        )
    )
    assert decision.applied is False
    assert decision.source is SourceLifecycle.TERMINAL


def test_supersede_with_no_target_is_denied(tmp_path: Path) -> None:
    _a, _m, evaluator, _c, _db = _setup(tmp_path)
    decision = evaluator.evaluate(
        BoundaryRequest(
            event=BoundaryEvent.SUPERSEDE,
            session_id=SESSION,
            turn_id=TURN,
            owner_agent=OWNER,
            new_seed=_seed(),
        )
    )
    assert decision.applied is False
    assert decision.source is SourceLifecycle.NONE


# --------------------------------------------------------------------------- #
# `terminalize`
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "transition_id,terminal_state,reason",
    [
        ("TR-001", "ST-901", "stop"),
        ("TR-025", "ST-902", "reject"),
        ("TR-028", "ST-902", "reject"),
        ("TR-030", "ST-900", "success"),
        ("TR-032", "ST-900", "success"),
    ],
)
def test_terminalize_sets_boundary_event_for_each_terminal_tr(
    tmp_path: Path, transition_id: str, terminal_state: str, reason: str
) -> None:
    adapter, _m, evaluator, _c, db_path = _setup(tmp_path)
    identity = _create(adapter, "wf-1")
    decision = evaluator.evaluate(
        BoundaryRequest(
            event=BoundaryEvent.TERMINALIZE,
            session_id=SESSION,
            turn_id=TURN,
            owner_agent=OWNER,
            target_workflow_id="wf-1",
            transition_id=transition_id,
        )
    )
    assert decision.applied is True
    assert decision.boundary_event == "terminalize"
    assert _read_boundary_event(db_path, "wf-1") == "terminalize"  # POL-014B

    record = adapter.read(identity)
    assert record.row.terminal.is_terminal is True
    assert record.row.terminal.terminal_state == terminal_state
    assert record.row.terminal.terminal_reason == reason
    assert record.row.owner_lock.active is None


def test_terminalize_with_explicit_terminal_state(tmp_path: Path) -> None:
    adapter, _m, evaluator, _c, _db = _setup(tmp_path)
    identity = _create(adapter, "wf-1")
    decision = evaluator.evaluate(
        BoundaryRequest(
            event=BoundaryEvent.TERMINALIZE,
            session_id=SESSION,
            turn_id=TURN,
            owner_agent=OWNER,
            target_workflow_id="wf-1",
            terminal_state="ST-901",
        )
    )
    assert decision.applied is True
    assert adapter.read(identity).row.terminal.terminal_state == "ST-901"


def test_terminalize_with_non_terminal_transition_falls_back_to_explicit_state(
    tmp_path: Path,
) -> None:
    # transition_id present but not a terminal TR → explicit terminal_state used.
    adapter, _m, evaluator, _c, _db = _setup(tmp_path)
    identity = _create(adapter, "wf-1")
    decision = evaluator.evaluate(
        BoundaryRequest(
            event=BoundaryEvent.TERMINALIZE,
            session_id=SESSION,
            turn_id=TURN,
            owner_agent=OWNER,
            target_workflow_id="wf-1",
            transition_id="TR-004",
            terminal_state="ST-900",
        )
    )
    assert decision.applied is True
    assert adapter.read(identity).row.terminal.terminal_state == "ST-900"


def test_terminalize_without_state_or_transition_raises(tmp_path: Path) -> None:
    adapter, _m, evaluator, _c, _db = _setup(tmp_path)
    _create(adapter, "wf-1")
    with pytest.raises(BoundaryRequestError, match="terminal transition_id or"):
        evaluator.evaluate(
            BoundaryRequest(
                event=BoundaryEvent.TERMINALIZE,
                session_id=SESSION,
                turn_id=TURN,
                owner_agent=OWNER,
                target_workflow_id="wf-1",
            )
        )


def test_terminalize_from_terminal_is_denied(tmp_path: Path) -> None:
    adapter, _m, evaluator, _c, _db = _setup(tmp_path)
    _create(adapter, "wf-1")
    evaluator.evaluate(
        BoundaryRequest(
            event=BoundaryEvent.TERMINALIZE,
            session_id=SESSION,
            turn_id=TURN,
            owner_agent=OWNER,
            target_workflow_id="wf-1",
            transition_id="TR-030",
        )
    )
    decision = evaluator.evaluate(
        BoundaryRequest(
            event=BoundaryEvent.TERMINALIZE,
            session_id=SESSION,
            turn_id=TURN,
            owner_agent=OWNER,
            target_workflow_id="wf-1",
            transition_id="TR-001",
        )
    )
    assert decision.applied is False
    assert decision.source is SourceLifecycle.TERMINAL


def test_default_clock_used_when_not_overridden(tmp_path: Path) -> None:
    # No clock override → the evaluator's default `_utcnow` is exercised.
    adapter = RuntimeStoreAdapter(tmp_path / "store.db")
    config = ControllerConfig()
    manager = LockManager(adapter, config)
    evaluator = LifecycleBoundaryEvaluator(adapter, manager)
    _create(adapter, "wf-1")
    decision = evaluator.evaluate(
        BoundaryRequest(
            event=BoundaryEvent.TERMINALIZE,
            session_id=SESSION,
            turn_id=TURN,
            owner_agent=OWNER,
            target_workflow_id="wf-1",
            transition_id="TR-030",
        )
    )
    assert decision.applied is True
    record = adapter.read(RuntimeIdentity(SESSION, "wf-1", TURN))
    assert record.row.terminal.terminalized_at is not None
