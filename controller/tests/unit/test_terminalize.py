"""Tests for terminal-transition `boundary_event = terminalize` enforcement (Task 7.5).

POL-014B: every terminal FSM transition (TR-001/025/028/030/032) MUST set
`boundary_event = terminalize` in the emitted snapshot.
"""

from __future__ import annotations

import pytest

from helm_controller.contracts.snapshot import Presend, Snapshot, ToolCalls
from helm_controller.lifecycle import terminalize
from helm_controller.lifecycle.terminalize import (
    TERMINAL_REASON_BY_STATE,
    TERMINAL_TRANSITIONS,
    TERMINALIZE_BOUNDARY_EVENT,
    TerminalizeViolation,
    assert_terminalize_present,
    enforce_terminalize,
    is_terminal_transition,
    terminal_boundary_event,
    terminal_state_for,
)

_TERMINAL_TRS = ["TR-001", "TR-025", "TR-028", "TR-030", "TR-032"]
_NON_TERMINAL_TRS = ["TR-002", "TR-003", "TR-004", "TR-033", "TR-034"]


def _snapshot(boundary_event: str | None) -> Snapshot:
    return Snapshot(
        session_id="s",
        workflow_id="w",
        session_active_workflow_id=None,
        predecessor_workflow_id=None,
        successor_workflow_id=None,
        workflow_lifecycle_before="non_terminal_active",
        workflow_lifecycle_after="terminal",
        turn_id="t",
        state_before="ST-080",
        state_after="ST-900",
        prior_non_terminal_fsm_state=None,
        owner_before="ARTHUR",
        owner_after="ARTHUR",
        event="EV-019",
        boundary_event=boundary_event,
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


def test_terminal_transitions_set_is_the_five_pol014b_trs() -> None:
    assert TERMINAL_TRANSITIONS == frozenset(_TERMINAL_TRS)


@pytest.mark.parametrize("transition_id", _TERMINAL_TRS)
def test_terminal_transition_recognized(transition_id: str) -> None:
    assert is_terminal_transition(transition_id) is True
    assert terminal_boundary_event(transition_id) == TERMINALIZE_BOUNDARY_EVENT


@pytest.mark.parametrize("transition_id", _NON_TERMINAL_TRS)
def test_non_terminal_transition_not_recognized(transition_id: str) -> None:
    assert is_terminal_transition(transition_id) is False
    assert terminal_boundary_event(transition_id) is None


@pytest.mark.parametrize("transition_id", _TERMINAL_TRS)
def test_enforce_sets_terminalize_on_terminal_transition(transition_id: str) -> None:
    stamped = enforce_terminalize(transition_id, _snapshot(None))
    assert stamped.boundary_event == TERMINALIZE_BOUNDARY_EVENT


def test_enforce_is_idempotent_when_already_set() -> None:
    snapshot = _snapshot(TERMINALIZE_BOUNDARY_EVENT)
    stamped = enforce_terminalize("TR-001", snapshot)
    assert stamped is snapshot


def test_enforce_leaves_non_terminal_snapshot_unchanged() -> None:
    snapshot = _snapshot(None)
    assert enforce_terminalize("TR-004", snapshot) is snapshot


@pytest.mark.parametrize("transition_id", _TERMINAL_TRS)
def test_assert_raises_when_terminalize_absent(transition_id: str) -> None:
    with pytest.raises(TerminalizeViolation) as excinfo:
        assert_terminalize_present(transition_id, _snapshot(None))
    assert excinfo.value.transition_id == transition_id
    assert excinfo.value.boundary_event is None


@pytest.mark.parametrize("transition_id", _TERMINAL_TRS)
def test_assert_passes_when_terminalize_present(transition_id: str) -> None:
    assert_terminalize_present(transition_id, _snapshot(TERMINALIZE_BOUNDARY_EVENT))


def test_assert_ignores_non_terminal_transition() -> None:
    # No exception even with no boundary_event — non-terminal TR is never a violation.
    assert_terminalize_present("TR-004", _snapshot(None))


def test_terminal_state_for_reads_from_fsm_table() -> None:
    assert terminal_state_for("TR-001") == "ST-901"
    assert terminal_state_for("TR-025") == "ST-902"
    assert terminal_state_for("TR-028") == "ST-902"
    assert terminal_state_for("TR-030") == "ST-900"
    assert terminal_state_for("TR-032") == "ST-900"


def test_terminal_state_for_rejects_non_terminal_transition() -> None:
    with pytest.raises(TerminalizeViolation):
        terminal_state_for("TR-004")


def test_terminal_reason_by_state_covers_all_terminal_states() -> None:
    assert TERMINAL_REASON_BY_STATE == {
        "ST-900": "success",
        "ST-901": "stop",
        "ST-902": "reject",
    }


def test_drift_guard_rejects_non_terminal_transition(monkeypatch: pytest.MonkeyPatch) -> None:
    # If the terminal set ever drifts to include a non-terminal TR, the
    # import-time invariant must fail fast (POL-014B source-of-truth guard).
    monkeypatch.setattr(terminalize, "TERMINAL_TRANSITIONS", frozenset({"TR-004"}))
    with pytest.raises(AssertionError, match="not a terminal state"):
        terminalize._assert_terminal_set_matches_fsm()
