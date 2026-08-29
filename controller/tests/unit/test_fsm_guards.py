"""Guard predicate tests (spec015 Task 5.5).

Every guard GD-001..GD-015 is invoked through :func:`evaluate_guard` with both a
truthy and a falsy snapshot context so each boolean predicate flips
independently. Also covers the ``guard_by_id`` found / not-found branches.
"""

from __future__ import annotations

from typing import Any

import pytest

from helm_controller.contracts.snapshot import Presend, Snapshot, ToolCalls
from helm_controller.fsm.guards import (
    Guard,
    UnknownGuardError,
    evaluate_guard,
    guard_by_id,
)


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


# (guard, truthy overrides, falsy overrides)
_CASES = [
    (Guard.GD_001, {"explicit_path": "standard"}, {"explicit_path": None}),
    (Guard.GD_002, {"doc_type": "spec"}, {"doc_type": "plan"}),
    (Guard.GD_003, {"doc_type": "plan"}, {"doc_type": "spec"}),
    (Guard.GD_004, {"doc_type": "non_gate"}, {"doc_type": "spec"}),
    (Guard.GD_005, {"open_question_count": 1}, {"open_question_count": 0}),
    (Guard.GD_006, {"open_question_count": 0}, {"open_question_count": 1}),
    (Guard.GD_007, {"owner_before": "orchestrator"}, {"owner_before": "clarifier"}),
    (Guard.GD_008, {"owner_before": "clarifier"}, {"owner_before": "orchestrator"}),
    (Guard.GD_009, {"state_before": "ST-010"}, {"state_before": "ST-900"}),
    (
        Guard.GD_010,
        {"presend": Presend(executed=True, result="pass", failed_check=None)},
        {"presend": Presend(executed=True, result="fail", failed_check="CHK-003")},
    ),
    (
        Guard.GD_011,
        {"workflow_lifecycle_before": "non_terminal_active"},
        {"workflow_lifecycle_before": "terminal"},
    ),
    (
        Guard.GD_012,
        {"workflow_lifecycle_before": "non_terminal_suspended"},
        {"workflow_lifecycle_before": "non_terminal_active"},
    ),
    (
        Guard.GD_013,
        {"session_active_workflow_id": "w", "workflow_id": "w"},
        {"session_active_workflow_id": None, "workflow_id": "w"},
    ),
    (Guard.GD_014, {"session_active_workflow_id": None}, {"session_active_workflow_id": "w"}),
    (Guard.GD_015, {"boundary_event": "supersede"}, {"boundary_event": None}),
]


@pytest.mark.parametrize("guard, truthy, falsy", _CASES, ids=[c[0].value for c in _CASES])
def test_guard_flips_with_context(
    guard: Guard, truthy: dict[str, Any], falsy: dict[str, Any]
) -> None:
    assert evaluate_guard(guard, make_snapshot(**truthy)) is True
    assert evaluate_guard(guard, make_snapshot(**falsy)) is False


def test_every_guard_has_a_case() -> None:
    assert {case[0] for case in _CASES} == set(Guard)


def test_guard_by_id_found_and_not_found() -> None:
    assert guard_by_id("GD-009") is Guard.GD_009
    with pytest.raises(UnknownGuardError):
        guard_by_id("GD-000")
