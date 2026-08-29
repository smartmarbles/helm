"""CHK-001..CHK-014 pre-send gate tests — POL-020/POL-021 (spec015 Task 6.5).

One isolated first-fail per check (each crafted so no lower-id check trips
first, proving ascending fail-fast), the full-pass path, ``presend.failed_check``
reason-id correctness with the ST-903 reroute, and confirmation that CHK-003
reuses the Phase 5 action-matrix legality check.
"""

from __future__ import annotations

from collections.abc import Callable

from helm_controller.contracts.snapshot import Presend, Snapshot, ToolCalls
from helm_controller.gates.presend_checks import run_presend_checks

SnapFactory = Callable[..., Snapshot]

_REQUIRED_KEYS = ["objective", "constraints", "inputs", "expected_output"]
_TRIPLE = ["quiz", "inline", "defer"]


def _assert_fail(snap: Snapshot, chk_id: str) -> None:
    result = run_presend_checks(snap)
    assert result.passed is False
    assert result.result == "fail"
    assert result.failed_check == chk_id
    assert result.decision is not None
    assert result.decision.reason_id == chk_id
    assert result.decision.state_after == "ST-903"


def test_all_checks_pass(snapshot_factory: SnapFactory) -> None:
    result = run_presend_checks(snapshot_factory())
    assert result.passed is True
    assert result.result == "pass"
    assert result.failed_check is None
    assert result.decision is None


def test_chk_001_stop_without_terminal_shape(snapshot_factory: SnapFactory) -> None:
    snap = snapshot_factory(pending_interrupt="stop", actions=[], state_after="ST-020")
    _assert_fail(snap, "CHK-001")


def test_chk_002_process_audit_missing_ack(snapshot_factory: SnapFactory) -> None:
    snap = snapshot_factory(pending_interrupt="process_audit", actions=[])
    _assert_fail(snap, "CHK-002")


def test_chk_003_reuses_action_matrix(snapshot_factory: SnapFactory) -> None:
    # AC-002 (dispatch) is forbidden in ST-010 per the Phase 5 matrix.
    snap = snapshot_factory(state_before="ST-010", actions=["AC-002"])
    _assert_fail(snap, "CHK-003")


def test_chk_004_orchestrator_deliverable(snapshot_factory: SnapFactory) -> None:
    snap = snapshot_factory(
        outbound_sender="orchestrator", outbound_message_type="deliverable_content"
    )
    _assert_fail(snap, "CHK-004")


def test_chk_005_clarifier_owner_question_prompt(snapshot_factory: SnapFactory) -> None:
    snap = snapshot_factory(
        owner_before="clarifier",
        outbound_sender="orchestrator",
        outbound_message_type="question_prompt",
    )
    _assert_fail(snap, "CHK-005")


def test_chk_006_prompt_options_wrong(snapshot_factory: SnapFactory) -> None:
    snap = snapshot_factory(open_question_count=1, prompt_options=["quiz"])
    _assert_fail(snap, "CHK-006")


def test_chk_007_clarifier_without_choice(snapshot_factory: SnapFactory) -> None:
    snap = snapshot_factory(
        state_before="ST-040",
        event="EV-011",
        open_question_count=1,
        prompt_options=_TRIPLE,
        user_choice=None,
        actions=["AC-004"],
    )
    _assert_fail(snap, "CHK-007")


def test_chk_008_gate_doc_open_questions(snapshot_factory: SnapFactory) -> None:
    snap = snapshot_factory(
        state_before="ST-060",
        doc_type="spec",
        open_question_count=1,
        prompt_options=_TRIPLE,
        user_choice="quiz",
        open_question_protocol_resolved=False,
        actions=["AC-005"],
    )
    _assert_fail(snap, "CHK-008")


def test_chk_009_execution_in_st070(snapshot_factory: SnapFactory) -> None:
    snap = snapshot_factory(
        state_before="ST-070",
        event="EV-005",
        phase_execution_started=True,
        actions=[],
    )
    _assert_fail(snap, "CHK-009")


def test_chk_010_path_divergence(snapshot_factory: SnapFactory) -> None:
    snap = snapshot_factory(explicit_path="full", selected_path="standard")
    _assert_fail(snap, "CHK-010")


def test_chk_011_dispatch_missing_keys(snapshot_factory: SnapFactory) -> None:
    snap = snapshot_factory(
        state_before="ST-020", actions=["AC-002"], dispatch_payload_keys=["objective"]
    )
    _assert_fail(snap, "CHK-011")


def test_chk_012_claimed_without_dispatch(snapshot_factory: SnapFactory) -> None:
    snap = snapshot_factory(
        delegation_claimed=True, tool_calls=ToolCalls(runSubagent=0)
    )
    _assert_fail(snap, "CHK-012")


def test_chk_013_duplicate_output_paths(snapshot_factory: SnapFactory) -> None:
    snap = snapshot_factory(output_paths=["a.md", "a.md"])
    _assert_fail(snap, "CHK-013")


def test_chk_014_event_from_terminal_state(snapshot_factory: SnapFactory) -> None:
    snap = snapshot_factory(state_before="ST-901", event="EV-005", actions=[])
    _assert_fail(snap, "CHK-014")
