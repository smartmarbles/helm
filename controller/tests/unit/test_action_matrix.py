"""Action-matrix legality tests — POL-004 §4 / CHK-003 (spec015 Task 5.5).

Covers :func:`is_allowed` for the unconditional ``Y`` and ``N`` cells and for
every conditional cell (each compound predicate flipped on both sides), the
:func:`check_action_matrix` pass / first-fail / exempt-control-action branches,
and POL-018 (AC-012 forbidden in all states).
"""

from __future__ import annotations

from typing import Any

from helm_controller.contracts.snapshot import Presend, Snapshot, ToolCalls
from helm_controller.fsm.action_matrix import (
    CHK_003,
    check_action_matrix,
    is_allowed,
)
from helm_controller.fsm.actions import Action
from helm_controller.fsm.states import State


def make_snapshot(**overrides: Any) -> Snapshot:
    base: dict[str, Any] = dict(
        session_id="s",
        workflow_id="w",
        session_active_workflow_id=None,
        predecessor_workflow_id=None,
        successor_workflow_id=None,
        workflow_lifecycle_before="non_terminal_active",
        workflow_lifecycle_after="non_terminal_active",
        turn_id="t",
        state_before="ST-010",
        state_after="ST-020",
        prior_non_terminal_fsm_state=None,
        owner_before="orchestrator",
        owner_after="orchestrator",
        event="EV-001",
        boundary_event=None,
        selected_path=None,
        explicit_path=None,
        doc_type=None,
        open_question_count=0,
        pending_interrupt="none",
        actions=[],
        outbound_sender="orchestrator",
        outbound_message_type="status",
        prompt_options=[],
        user_choice=None,
        approval_prompted=False,
        open_question_protocol_resolved=False,
        delegation_claimed=False,
        dispatch_payload_keys=[],
        phase_execution_started=False,
        suppressed_action_ids=[],
        tool_calls=ToolCalls(runSubagent=0),
        presend=Presend(executed=True, result="pass", failed_check=None),
        output_paths=[],
    )
    base.update(overrides)
    return Snapshot(**base)


# ---------------------------------------------------------------------------
# Unconditional cells
# ---------------------------------------------------------------------------


def test_is_allowed_unconditional_yes() -> None:
    assert is_allowed(State.ROUTE_SELECTION, Action.ROUTE_REQUEST, make_snapshot()) is True


def test_is_allowed_unconditional_no() -> None:
    assert is_allowed(State.IDLE, Action.ROUTE_REQUEST, make_snapshot()) is False


def test_ack_stop_allowed_in_every_non_terminal_state() -> None:
    snap = make_snapshot()
    for state in State:
        expected = state not in {State.COMPLETED, State.STOPPED, State.REJECTED}
        assert is_allowed(state, Action.ACK_STOP, snap) is expected


def test_pol_018_direct_deliverable_forbidden_everywhere() -> None:
    snap = make_snapshot()
    for state in State:
        assert is_allowed(state, Action.DIRECT_DELIVERABLE_BY_ORCHESTRATOR, snap) is False


# ---------------------------------------------------------------------------
# Conditional cells — both arms of each predicate
# ---------------------------------------------------------------------------


def test_st030_open_question_prompt_conditional() -> None:
    state, action = State.WAIT_SUBAGENT, Action.PROMPT_OPEN_QUESTION_OPTIONS
    assert is_allowed(state, action, make_snapshot(open_question_count=1)) is True
    assert is_allowed(state, action, make_snapshot(open_question_count=0)) is False


def test_st030_approval_conditional_both_conditions() -> None:
    state, action = State.WAIT_SUBAGENT, Action.PROMPT_APPROVAL
    assert is_allowed(state, action, make_snapshot(open_question_count=0, doc_type="spec")) is True
    # first condition false (questions present)
    assert is_allowed(state, action, make_snapshot(open_question_count=1, doc_type="spec")) is False
    # second condition false (non-gate doc)
    assert is_allowed(state, action, make_snapshot(open_question_count=0, doc_type="non_gate")) is False


def test_st040_invoke_clarifier_conditional() -> None:
    state, action = State.WAIT_OPEN_QUESTION_CHOICE, Action.INVOKE_CLARIFIER
    assert is_allowed(state, action, make_snapshot(event="EV-011")) is True
    assert is_allowed(state, action, make_snapshot(event="EV-012")) is True
    assert is_allowed(state, action, make_snapshot(event="EV-013")) is False


def test_st040_approval_conditional_both_conditions() -> None:
    state, action = State.WAIT_OPEN_QUESTION_CHOICE, Action.PROMPT_APPROVAL
    assert is_allowed(state, action, make_snapshot(event="EV-013", doc_type="spec")) is True
    # first condition false (not defer)
    assert is_allowed(state, action, make_snapshot(event="EV-011", doc_type="spec")) is False
    # second condition false (non-gate doc)
    assert is_allowed(state, action, make_snapshot(event="EV-013", doc_type="non_gate")) is False


def test_st060_dispatch_revise_only() -> None:
    state, action = State.WAIT_SPEC_APPROVAL, Action.DISPATCH_SUBAGENT
    assert is_allowed(state, action, make_snapshot(event="EV-016")) is True
    assert is_allowed(state, action, make_snapshot(event="EV-015")) is False


def test_st070_dispatch_revise_only() -> None:
    state, action = State.WAIT_PLAN_APPROVAL, Action.DISPATCH_SUBAGENT
    assert is_allowed(state, action, make_snapshot(event="EV-016")) is True
    assert is_allowed(state, action, make_snapshot(event="EV-015")) is False


def test_st070_execute_phase_after_approve_only() -> None:
    state, action = State.WAIT_PLAN_APPROVAL, Action.EXECUTE_PHASE
    assert is_allowed(state, action, make_snapshot(event="EV-015")) is True
    assert is_allowed(state, action, make_snapshot(event="EV-018")) is False


# ---------------------------------------------------------------------------
# CHK-003 check
# ---------------------------------------------------------------------------


def test_check_passes_when_all_governed_actions_allowed() -> None:
    result = check_action_matrix(
        State.ROUTE_SELECTION, [Action.ROUTE_REQUEST], make_snapshot()
    )
    assert result.passed is True
    assert result.failed_action is None
    assert result.decision is None


def test_check_fails_on_forbidden_action() -> None:
    result = check_action_matrix(
        State.IDLE, [Action.ROUTE_REQUEST], make_snapshot()
    )
    assert result.passed is False
    assert result.failed_action == "AC-001"
    assert result.decision is not None
    assert result.decision.decision == "deny"
    assert result.decision.reason_id == CHK_003
    assert result.decision.state_after == "ST-903"


def test_check_skips_exempt_control_actions() -> None:
    # AC-008 (Y in ST-000) plus AC-011 (exempt control action) → passes.
    result = check_action_matrix(
        State.IDLE, [Action.ACK_STOP, Action.MARK_TERMINAL], make_snapshot()
    )
    assert result.passed is True
    assert result.failed_action is None


def test_check_first_fail_is_reported() -> None:
    # AC-001 forbidden in ST-000 reported before AC-002 is even examined.
    result = check_action_matrix(
        State.IDLE,
        [Action.ROUTE_REQUEST, Action.DISPATCH_SUBAGENT],
        make_snapshot(),
    )
    assert result.failed_action == "AC-001"
