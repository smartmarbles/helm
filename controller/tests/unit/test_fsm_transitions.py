"""Transition evaluator tests (spec015 Task 5.5).

Covers every TR-001..TR-035 happy-path (guards satisfied, correct destination
and actions), illegal-transition emission when no TR matches, guard-miss
fall-through, and the TR-003 / TR-034 dynamic-destination resolution from the
snapshot's ``prior_non_terminal_fsm_state`` (including the unresolved-null case).
"""

from __future__ import annotations

from typing import Any

import pytest

from helm_controller.contracts.snapshot import Presend, Snapshot, ToolCalls
from helm_controller.fsm.evaluator import (
    ILLEGAL_TRANSITION_REASON_ID,
    evaluate,
)
from helm_controller.fsm.events import Event
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


_PASS = {"presend": Presend(executed=True, result="pass", failed_check=None)}

# (TR id, state_before, event id, guard overrides, expected to-state, expected actions)
_CASES: list[tuple[str, State, str, dict[str, Any], str, tuple[str, ...]]] = [
    ("TR-001", State.ROUTE_SELECTION, "EV-002", {}, "ST-901", ("AC-008", "AC-011")),
    ("TR-002", State.ROUTE_SELECTION, "EV-003", {}, "ST-090", ("AC-007",)),
    ("TR-003", State.PROCESS_AUDIT, "EV-022", {"prior_non_terminal_fsm_state": "ST-070"}, "ST-070", ("AC-010",)),
    ("TR-004", State.IDLE, "EV-001", {}, "ST-010", ("AC-001",)),
    ("TR-005", State.ROUTE_SELECTION, "EV-004", {}, "ST-020", ()),
    ("TR-006", State.PREPARE_DISPATCH, "EV-021", _PASS, "ST-030", ("AC-002",)),
    ("TR-007", State.PREPARE_DISPATCH, "EV-020", {}, "ST-903", ("AC-009",)),
    ("TR-008", State.PRE_SEND_BLOCKED, "EV-021", _PASS, "ST-020", ()),
    ("TR-009", State.WAIT_SUBAGENT, "EV-006", {"doc_type": "spec", "open_question_count": 1}, "ST-040", ("AC-003",)),
    ("TR-010", State.WAIT_SUBAGENT, "EV-007", {"doc_type": "plan", "open_question_count": 1}, "ST-040", ("AC-003",)),
    ("TR-011", State.WAIT_SUBAGENT, "EV-008", {"doc_type": "non_gate", "open_question_count": 1}, "ST-040", ("AC-003",)),
    ("TR-012", State.WAIT_SUBAGENT, "EV-006", {"doc_type": "spec", "open_question_count": 0}, "ST-060", ("AC-005",)),
    ("TR-013", State.WAIT_SUBAGENT, "EV-007", {"doc_type": "plan", "open_question_count": 0}, "ST-070", ("AC-005",)),
    ("TR-014", State.WAIT_SUBAGENT, "EV-008", {"doc_type": "non_gate", "open_question_count": 0}, "ST-020", ()),
    ("TR-015", State.WAIT_OPEN_QUESTION_CHOICE, "EV-011", {}, "ST-050", ("AC-004",)),
    ("TR-016", State.WAIT_OPEN_QUESTION_CHOICE, "EV-012", {}, "ST-050", ("AC-004",)),
    ("TR-017", State.WAIT_OPEN_QUESTION_CHOICE, "EV-013", {"doc_type": "spec"}, "ST-060", ("AC-005",)),
    ("TR-018", State.WAIT_OPEN_QUESTION_CHOICE, "EV-013", {"doc_type": "plan"}, "ST-070", ("AC-005",)),
    ("TR-019", State.WAIT_OPEN_QUESTION_CHOICE, "EV-013", {"doc_type": "non_gate"}, "ST-020", ()),
    ("TR-020", State.CLARIFIER_OWNED, "EV-014", {"doc_type": "spec"}, "ST-060", ("AC-005",)),
    ("TR-021", State.CLARIFIER_OWNED, "EV-014", {"doc_type": "plan"}, "ST-070", ("AC-005",)),
    ("TR-022", State.CLARIFIER_OWNED, "EV-014", {"doc_type": "non_gate"}, "ST-020", ()),
    ("TR-023", State.WAIT_SPEC_APPROVAL, "EV-015", {}, "ST-020", ()),
    ("TR-024", State.WAIT_SPEC_APPROVAL, "EV-016", {}, "ST-020", ()),
    ("TR-025", State.WAIT_SPEC_APPROVAL, "EV-017", {}, "ST-902", ("AC-011",)),
    ("TR-026", State.WAIT_PLAN_APPROVAL, "EV-015", {}, "ST-080", ()),
    ("TR-027", State.WAIT_PLAN_APPROVAL, "EV-016", {}, "ST-020", ()),
    ("TR-028", State.WAIT_PLAN_APPROVAL, "EV-017", {}, "ST-902", ("AC-011",)),
    ("TR-029", State.EXECUTE_PHASES, "EV-018", {}, "ST-080", ("AC-006",)),
    ("TR-030", State.EXECUTE_PHASES, "EV-019", {}, "ST-900", ("AC-011",)),
    ("TR-031", State.COMPLETED, "EV-001", {}, "ST-010", ("AC-001",)),
    ("TR-032", State.PREPARE_DISPATCH, "EV-023", {}, "ST-900", ("AC-011",)),
    ("TR-033", State.EXECUTE_PHASES, "EV-024", {"workflow_lifecycle_before": "non_terminal_active", "session_active_workflow_id": "w", "workflow_id": "w"}, "ST-000", ()),
    ("TR-034", State.IDLE, "EV-025", {"workflow_lifecycle_before": "non_terminal_suspended", "session_active_workflow_id": None, "prior_non_terminal_fsm_state": "ST-070"}, "ST-070", ()),
    ("TR-035", State.EXECUTE_PHASES, "EV-001", {"workflow_lifecycle_before": "non_terminal_active", "session_active_workflow_id": "w", "workflow_id": "w", "boundary_event": "supersede"}, "ST-010", ("AC-001", "AC-011")),
]


@pytest.mark.parametrize(
    "tr_id, state, event_id, overrides, to_state, actions",
    _CASES,
    ids=[case[0] for case in _CASES],
)
def test_transition_happy_path(
    tr_id: str,
    state: State,
    event_id: str,
    overrides: dict[str, Any],
    to_state: str,
    actions: tuple[str, ...],
) -> None:
    merged = dict(overrides)
    merged.setdefault("state_before", state.value)
    result = evaluate(state, Event(event_id), make_snapshot(**merged))
    assert result.legal is True, f"{tr_id} should be legal"
    assert result.transition_id == tr_id
    assert result.state_after == to_state
    assert result.actions == actions
    assert result.decision is None


def test_every_transition_has_a_happy_path_case() -> None:
    assert [case[0] for case in _CASES] == [f"TR-{n:03d}" for n in range(1, 36)]


# ---------------------------------------------------------------------------
# Illegal-transition emission (failure mode 1, spec §6.4)
# ---------------------------------------------------------------------------


def test_no_matching_transition_emits_illegal() -> None:
    result = evaluate(
        State.CLARIFIER_OWNED,
        Event.USER_WORK_REQUEST,
        make_snapshot(state_before="ST-050"),
    )
    assert result.legal is False
    assert result.transition_id is None
    assert result.state_after == "ST-903"
    assert result.actions == ()
    assert result.decision is not None
    assert result.decision.decision == "deny"
    assert result.decision.reason_id == ILLEGAL_TRANSITION_REASON_ID
    assert result.decision.state_after == "ST-903"


def test_guard_miss_falls_through_to_illegal() -> None:
    # ST-020 + EV-021 requires GD-010 (presend pass); a failing presend misses
    # TR-006 and TR-008 (wrong source), yielding the illegal emission.
    result = evaluate(
        State.PREPARE_DISPATCH,
        Event.PRE_SEND_PASS,
        make_snapshot(
            state_before="ST-020",
            presend=Presend(executed=True, result="fail", failed_check="CHK-003"),
        ),
    )
    assert result.legal is False
    assert result.decision is not None
    assert result.decision.reason_id == ILLEGAL_TRANSITION_REASON_ID


def test_dynamic_destination_unresolved_is_illegal() -> None:
    # TR-003 matches on (ST-090, EV-022) but prior_non_terminal_fsm_state is null.
    result = evaluate(
        State.PROCESS_AUDIT,
        Event.AUDIT_RESPONSE_SENT,
        make_snapshot(state_before="ST-090", prior_non_terminal_fsm_state=None),
    )
    assert result.legal is False
    assert result.transition_id is None
    assert result.state_after == "ST-903"
    assert result.decision is not None
    assert "prior_non_terminal_fsm_state" in result.decision.reason


def test_tr034_resolves_dynamic_destination() -> None:
    result = evaluate(
        State.IDLE,
        Event.USER_RESUME_WORKFLOW,
        make_snapshot(
            state_before="ST-000",
            workflow_lifecycle_before="non_terminal_suspended",
            session_active_workflow_id=None,
            prior_non_terminal_fsm_state="ST-080",
        ),
    )
    assert result.legal is True
    assert result.transition_id == "TR-034"
    assert result.state_after == "ST-080"
