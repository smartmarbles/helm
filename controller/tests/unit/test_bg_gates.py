"""BG-001..BG-006 hard-gate evaluator tests — POL-054 (spec015 Task 6.5).

Covers each gate's pass and fail path, ascending fail-fast (a later gate is
``not_evaluated`` once an earlier one fails), the §11.3 blocked behaviour
(suppressed actions, ST-903 reroute conditioned on non-terminal, BG-006 terminal
mutation rejection), and the gate predicates' inner branches by direct call.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from helm_controller.contracts.blackboard import (
    Audit,
    BlackboardRow,
    OwnerLock,
    Terminal,
)
from helm_controller.contracts.snapshot import Presend, Snapshot, ToolCalls
from helm_controller.gates import bg_rules
from helm_controller.gates.bg_evaluator import evaluate_blackboard_gates
from helm_controller.gates.bg_rules import GateStatus

NOW = datetime(2026, 5, 31, 12, 0, 0, tzinfo=timezone.utc)
_FUTURE = "2026-12-31T00:00:00Z"
_PAST = "2026-01-01T00:00:00Z"


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
        state_before="ST-030",
        state_after="ST-040",
        prior_non_terminal_fsm_state=None,
        owner_before="orchestrator",
        owner_after="orchestrator",
        event="EV-005",
        boundary_event=None,
        selected_path=None,
        explicit_path=None,
        doc_type=None,
        open_question_count=0,
        pending_interrupt="none",
        actions=["AC-002"],
        outbound_sender="orchestrator",
        outbound_message_type="status",
        prompt_options=[],
        user_choice=None,
        approval_prompted=False,
        open_question_protocol_resolved=True,
        delegation_claimed=False,
        dispatch_payload_keys=[],
        phase_execution_started=False,
        suppressed_action_ids=[],
        tool_calls=ToolCalls(runSubagent=1),
        presend=Presend(executed=True, result="pass", failed_check=None),
        output_paths=[],
    )
    base.update(overrides)
    return Snapshot(**base)


def make_blackboard(**overrides: Any) -> BlackboardRow:
    lock_overrides = overrides.pop("owner_lock", {})
    terminal_overrides = overrides.pop("terminal", {})
    lock = dict(
        active="ARTHUR",
        lock_token="tok",
        acquired_at="2026-05-31T11:00:00Z",
        expires_at=_FUTURE,
        is_stale=False,
        active_lock_count=1,
    )
    lock.update(lock_overrides)
    terminal = dict(
        is_terminal=False,
        terminal_state=None,
        terminalized_at=None,
        terminal_reason=None,
    )
    terminal.update(terminal_overrides)
    base: dict[str, Any] = dict(
        row_present=True,
        row_schema_valid=True,
        row_id="BBR-000001",
        session_id="s",
        workflow_id="w",
        predecessor_workflow_id=None,
        successor_workflow_id=None,
        item_id="item",
        lifecycle_stage="dispatch",
        workflow_lifecycle="non_terminal_active",
        fsm_state_ref="ST-030",
        prior_non_terminal_fsm_state=None,
        owner_lock=OwnerLock(**lock),
        gates={g: "pass" for g in bg_rules.BG_ORDER},
        required_gates_passed=True,
        terminal=Terminal(**terminal),
        audit=Audit(
            created_at="2026-05-31T10:00:00Z",
            created_by="ARTHUR",
            revision=1,
            immutable_fields_hash="h",
            audit_fields_mutated=False,
        ),
        mutation_attempt_keys=[],
    )
    base.update(overrides)
    return BlackboardRow(**base)


def _status(result: Any, gate_id: str) -> GateStatus:
    return {o.gate_id: o.status for o in result.outcomes}[gate_id]


# --- happy path ------------------------------------------------------------


def test_all_gates_pass() -> None:
    result = evaluate_blackboard_gates(make_snapshot(), make_blackboard(), now=NOW)
    assert result.passed is True
    assert result.first_failure_id is None
    assert result.decision is None
    assert result.required_gates_passed is True
    assert all(o.status is GateStatus.PASS for o in result.outcomes)


# --- BG-001 + fail-fast ----------------------------------------------------


def test_bg_001_fail_suppresses_and_routes_st903() -> None:
    bb = make_blackboard(row_schema_valid=False)
    result = evaluate_blackboard_gates(make_snapshot(), bb, now=NOW)
    assert result.passed is False
    assert result.first_failure_id == "BG-001"
    assert _status(result, "BG-001") is GateStatus.BLOCKED
    # fail-fast: BG-004 must NOT be evaluated once BG-001 fails.
    assert _status(result, "BG-004") is GateStatus.NOT_EVALUATED
    assert result.route_to_st903 is True
    assert result.suppressed_action_ids == ("AC-002",)
    assert result.decision is not None
    assert result.decision.reason_id == "BG-001"
    assert result.decision.state_after == "ST-903"
    assert result.required_gates_passed is False


def test_bg_001_fail_in_terminal_state_does_not_route() -> None:
    bb = make_blackboard(row_schema_valid=False)
    snap = make_snapshot(state_before="ST-900", actions=[])
    result = evaluate_blackboard_gates(snap, bb, now=NOW)
    assert result.first_failure_id == "BG-001"
    assert result.route_to_st903 is False
    assert result.decision is not None
    assert result.decision.state_after == "ST-900"
    assert result.decision.suppressed_action_ids is None


# --- BG-002 (three distinct failure causes) --------------------------------


def test_bg_002_fail_state_ref_mismatch() -> None:
    bb = make_blackboard(fsm_state_ref="ST-020")
    result = evaluate_blackboard_gates(make_snapshot(), bb, now=NOW)
    assert result.first_failure_id == "BG-002"


def test_bg_002_fail_stage_does_not_contain_state() -> None:
    bb = make_blackboard(lifecycle_stage="route")  # allows only ST-010
    result = evaluate_blackboard_gates(make_snapshot(), bb, now=NOW)
    assert result.first_failure_id == "BG-002"


def test_bg_002_fail_unknown_stage() -> None:
    bb = make_blackboard(lifecycle_stage="bogus")
    result = evaluate_blackboard_gates(make_snapshot(), bb, now=NOW)
    assert result.first_failure_id == "BG-002"


# --- BG-003 (stale lock + direct predicate branches) -----------------------


def test_bg_003_fail_stale_lock() -> None:
    bb = make_blackboard(owner_lock={"is_stale": True})
    result = evaluate_blackboard_gates(make_snapshot(), bb, now=NOW)
    assert result.first_failure_id == "BG-003"
    assert result.route_to_st903 is True


def test_bg_003_fail_expired_lock() -> None:
    bb = make_blackboard(owner_lock={"expires_at": _PAST})
    result = evaluate_blackboard_gates(make_snapshot(), bb, now=NOW)
    assert result.first_failure_id == "BG-003"


def test_bg_003_pass_suspended_no_lock_branch() -> None:
    prior: dict[str, GateStatus] = {}
    bb = make_blackboard(
        workflow_lifecycle="non_terminal_suspended",
        owner_lock={"active": None, "active_lock_count": 0, "expires_at": None},
    )
    assert bg_rules.bg_003(make_snapshot(), bb, prior, NOW) is True


def test_bg_003_expires_at_none_active_branch_fails() -> None:
    prior: dict[str, GateStatus] = {}
    bb = make_blackboard(owner_lock={"expires_at": None})
    assert bg_rules.bg_003(make_snapshot(), bb, prior, NOW) is False


def test_bg_003_pass_naive_future_expiry() -> None:
    # A naive (offset-less) timestamp exercises the tz-normalization path.
    prior: dict[str, GateStatus] = {}
    bb = make_blackboard(owner_lock={"expires_at": "2026-12-31T00:00:00"})
    assert bg_rules.bg_003(make_snapshot(), bb, prior, NOW) is True


# --- BG-004 direct predicate branches --------------------------------------


def test_bg_004_pass_when_no_dispatch() -> None:
    prior: dict[str, GateStatus] = {}
    snap = make_snapshot(actions=[])
    assert bg_rules.bg_004(snap, make_blackboard(), prior, NOW) is True


def test_bg_004_fail_when_prior_gate_not_pass() -> None:
    prior = {
        "BG-001": GateStatus.BLOCKED,
        "BG-002": GateStatus.PASS,
        "BG-003": GateStatus.PASS,
    }
    assert bg_rules.bg_004(make_snapshot(), make_blackboard(), prior, NOW) is False


# --- BG-005 (execution-entry gate) -----------------------------------------


def test_bg_005_fail_execution_without_resolved_protocol() -> None:
    snap = make_snapshot(
        actions=["AC-002", "AC-006"],
        state_after="ST-080",
        open_question_protocol_resolved=False,
    )
    result = evaluate_blackboard_gates(snap, make_blackboard(), now=NOW)
    assert result.first_failure_id == "BG-005"
    assert result.suppressed_action_ids == ("AC-006",)
    assert result.route_to_st903 is True


def test_bg_005_pass_when_not_entering_execution() -> None:
    prior: dict[str, GateStatus] = {}
    snap = make_snapshot(state_after="ST-040")
    assert bg_rules.bg_005(snap, make_blackboard(), prior, NOW) is True


# --- BG-006 (terminal mutation rejection, TC-120) --------------------------


def test_bg_006_fail_terminal_mutation_rejected() -> None:
    snap = make_snapshot(state_before="ST-900", state_after="ST-900", actions=[])
    bb = make_blackboard(
        lifecycle_stage="terminal",
        fsm_state_ref="ST-900",
        workflow_lifecycle="terminal",
        owner_lock={"active": None, "active_lock_count": 0, "expires_at": None},
        terminal={
            "is_terminal": True,
            "terminal_state": "ST-900",
            "terminal_reason": "success",
        },
        mutation_attempt_keys=["owner_lock.active"],
    )
    result = evaluate_blackboard_gates(snap, bb, now=NOW)
    assert result.first_failure_id == "BG-006"
    assert result.mutation_rejected is True
    assert result.route_to_st903 is False
    assert result.decision is not None
    assert result.decision.state_after == "ST-900"
    assert result.suppressed_action_ids == ()
