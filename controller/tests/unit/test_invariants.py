"""INV-001..INV-021 invariant evaluator tests — POL-045 (spec015 Task 6.5).

One pass and one isolated fail per invariant (each fail crafted so no lower-id
invariant trips first), the all-pass path, multi-violation first-id selection,
and INV-021 ``registry_role`` resolution for a known agent, an unregistered
agent, and the null-lock (suspended/terminal) branch.
"""

from __future__ import annotations

from collections.abc import Callable

from helm_controller.contracts.blackboard import BlackboardRow
from helm_controller.contracts.snapshot import Presend, Snapshot, ToolCalls
from helm_controller.invariants.inv_evaluator import evaluate_invariants
from helm_controller.policy.registry import AgentRoleRegistry

_RESOLVE = AgentRoleRegistry().resolve_role

SnapFactory = Callable[..., Snapshot]
BoardFactory = Callable[..., BlackboardRow]

_REQUIRED_KEYS = ["objective", "constraints", "inputs", "expected_output"]
_TRIPLE = ["quiz", "inline", "defer"]


def _first(snap: Snapshot, board: BlackboardRow) -> str | None:
    return evaluate_invariants(snap, board, _RESOLVE).first_failure_id


def test_all_invariants_pass(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    result = evaluate_invariants(
        snapshot_factory(), blackboard_factory(), _RESOLVE
    )
    assert result.passed is True
    assert result.first_failure_id is None
    assert result.violations == ()
    assert result.decision is None


def test_inv_001_orchestrator_deliverable(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    snap = snapshot_factory(
        outbound_sender="orchestrator", outbound_message_type="deliverable_content"
    )
    assert _first(snap, blackboard_factory()) == "INV-001"


def test_inv_002_claimed_without_dispatch(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    snap = snapshot_factory(
        delegation_claimed=True, tool_calls=ToolCalls(runSubagent=0)
    )
    assert _first(snap, blackboard_factory()) == "INV-002"


def test_inv_003_path_divergence(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    snap = snapshot_factory(explicit_path="full", selected_path="standard")
    assert _first(snap, blackboard_factory()) == "INV-003"


def test_inv_004_prompt_options_wrong(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    snap = snapshot_factory(open_question_count=1, prompt_options=["quiz"])
    assert _first(snap, blackboard_factory()) == "INV-004"


def test_inv_005_clarifier_without_choice(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    snap = snapshot_factory(
        open_question_count=1,
        prompt_options=_TRIPLE,
        user_choice=None,
        actions=["AC-004"],
    )
    assert _first(snap, blackboard_factory()) == "INV-005"


def test_inv_006_spec_open_questions(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    snap = snapshot_factory(
        doc_type="spec",
        open_question_count=1,
        prompt_options=_TRIPLE,
        open_question_protocol_resolved=False,
        actions=["AC-005"],
    )
    assert _first(snap, blackboard_factory()) == "INV-006"


def test_inv_007_plan_open_questions(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    snap = snapshot_factory(
        doc_type="plan",
        open_question_count=1,
        prompt_options=_TRIPLE,
        open_question_protocol_resolved=False,
        actions=["AC-005"],
    )
    assert _first(snap, blackboard_factory()) == "INV-007"


def test_inv_008_execution_in_st070_without_approve(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    snap = snapshot_factory(
        state_before="ST-070", event="EV-005", phase_execution_started=True
    )
    assert _first(snap, blackboard_factory()) == "INV-008"


def test_inv_009_clarifier_owner_question_prompt(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    snap = snapshot_factory(
        owner_before="clarifier",
        outbound_sender="orchestrator",
        outbound_message_type="question_prompt",
    )
    assert _first(snap, blackboard_factory()) == "INV-009"


def test_inv_010_stop_without_terminal_shape(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    snap = snapshot_factory(event="EV-002", state_after="ST-020", actions=[])
    assert _first(snap, blackboard_factory()) == "INV-010"


def test_inv_011_process_audit_with_dispatch(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    snap = snapshot_factory(
        event="EV-003",
        state_after="ST-090",
        actions=["AC-002"],
        dispatch_payload_keys=_REQUIRED_KEYS,
    )
    assert _first(snap, blackboard_factory()) == "INV-011"


def test_inv_012_presend_not_executed(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    snap = snapshot_factory(
        presend=Presend(executed=False, result="pass", failed_check=None)
    )
    assert _first(snap, blackboard_factory()) == "INV-012"


def test_inv_013_dispatch_missing_keys(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    snap = snapshot_factory(actions=["AC-002"], dispatch_payload_keys=["objective"])
    assert _first(snap, blackboard_factory()) == "INV-013"


def test_inv_014_duplicate_output_paths(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    snap = snapshot_factory(output_paths=["a.md", "a.md"])
    assert _first(snap, blackboard_factory()) == "INV-014"


def test_inv_015_event_from_terminal_state(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    snap = snapshot_factory(state_before="ST-901", event="EV-005")
    assert _first(snap, blackboard_factory()) == "INV-015"


def test_inv_016_non_gate_defer_approval(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    snap = snapshot_factory(
        doc_type="non_gate", user_choice="defer", approval_prompted=True
    )
    assert _first(snap, blackboard_factory()) == "INV-016"


def test_inv_017_gate_defer_no_approval(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    snap = snapshot_factory(
        doc_type="spec", user_choice="defer", approval_prompted=False
    )
    assert _first(snap, blackboard_factory()) == "INV-017"


def test_inv_018_dispatch_without_row(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    snap = snapshot_factory(actions=["AC-002"], dispatch_payload_keys=_REQUIRED_KEYS)
    board = blackboard_factory(row_present=False)
    assert _first(snap, board) == "INV-018"


def test_inv_019_entered_gated_state_without_gates(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    snap = snapshot_factory(state_after="ST-030")
    board = blackboard_factory(required_gates_passed=False)
    assert _first(snap, board) == "INV-019"


def test_inv_020_audit_mutation_on_terminal(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    board = blackboard_factory(
        terminal={"is_terminal": True, "terminal_state": "ST-900"},
        audit={"audit_fields_mutated": True},
    )
    assert _first(snapshot_factory(), board) == "INV-020"


def test_inv_021_unregistered_owner_role(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    board = blackboard_factory(owner_lock={"active": "NOBODY"})
    assert _first(snapshot_factory(), board) == "INV-021"


def test_inv_021_pass_known_owner_role(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    result = evaluate_invariants(
        snapshot_factory(), blackboard_factory(owner_lock={"active": "ARTHUR"}), _RESOLVE
    )
    assert result.passed is True


def test_inv_021_pass_suspended_null_lock_branch(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    board = blackboard_factory(
        workflow_lifecycle="non_terminal_suspended",
        owner_lock={"active": None, "active_lock_count": 0, "expires_at": None},
    )
    result = evaluate_invariants(snapshot_factory(), board, _RESOLVE)
    assert result.passed is True


def test_multiple_violations_report_lowest_id(
    snapshot_factory: SnapFactory, blackboard_factory: BoardFactory
) -> None:
    snap = snapshot_factory(
        outbound_sender="orchestrator",
        outbound_message_type="deliverable_content",
        presend=Presend(executed=False, result="pass", failed_check=None),
    )
    result = evaluate_invariants(snap, blackboard_factory(), _RESOLVE)
    assert result.passed is False
    assert result.first_failure_id == "INV-001"
    ids = [v.invariant_id for v in result.violations]
    assert ids == ["INV-001", "INV-012"]
    assert result.decision is not None
    assert result.decision.reason_id == "INV-001"
