"""Core TC replay logic — drives Phase 8 evaluators turn-by-turn from fixture data.

Used by both the integration harness (tests/integration/harness.py) and by the
HK-008 LENS hook entry point (hk_lens.py).  This module lives in the source
tree so that audit/hk_lens.py can import it without crossing the test/src
boundary.

Each TC fixture entry has the form::

    {
        "tc_id":              "TC-001",
        "category":           "happy",
        "description":        "...",
        "turns": [
            {
                "snapshot_overrides": {...},
                "blackboard_overrides": {...} | null
            }
        ],
        "expected_verdict":        "PASS" | "FAIL",
        "expected_failed_check":   null | "CHK-###" | "INV-###" | "BG-###",
        "expected_state_after":    null | "ST-###"
    }

``snapshot_overrides`` is merged over ``BASE_SNAPSHOT``; ``blackboard_overrides``
over ``BASE_BLACKBOARD`` (nested dicts merged one level deep).  ``null`` for
``blackboard_overrides`` means no blackboard is supplied: BG-gate and invariant
stages are skipped for that turn.

Composite-identity check: session_id, workflow_id, and turn_id must all be
non-empty strings.  A failure returns ``failed_check="IDENTITY_COMPOSITE"``
before any BG/INV/presend evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from helm_controller.contracts.blackboard import BlackboardRow
from helm_controller.contracts.snapshot import Snapshot
from helm_controller.gates.bg_evaluator import evaluate_blackboard_gates
from helm_controller.gates.presend_checks import run_presend_checks
from helm_controller.invariants.inv_evaluator import evaluate_invariants
from helm_controller.policy.registry import AgentRoleRegistry

_REGISTRY = AgentRoleRegistry()
_NOW = datetime(2026, 5, 31, 12, 0, 0, tzinfo=timezone.utc)

# ---------------------------------------------------------------------------
# Base fixture defaults (mirrors tests/unit/conftest.py factory defaults)
# ---------------------------------------------------------------------------

BASE_SNAPSHOT: dict[str, Any] = {
    "session_id": "sess-001",
    "workflow_id": "wf-001",
    "session_active_workflow_id": "wf-001",
    "predecessor_workflow_id": None,
    "successor_workflow_id": None,
    "workflow_lifecycle_before": "non_terminal_active",
    "workflow_lifecycle_after": "non_terminal_active",
    "turn_id": "t-001",
    "state_before": "ST-010",
    "state_after": "ST-020",
    "prior_non_terminal_fsm_state": None,
    "owner_before": "orchestrator",
    "owner_after": "orchestrator",
    "event": "EV-001",
    "boundary_event": None,
    "selected_path": None,
    "explicit_path": None,
    "doc_type": None,
    "open_question_count": 0,
    "pending_interrupt": "none",
    "actions": [],
    "outbound_sender": "orchestrator",
    "outbound_message_type": "status",
    "prompt_options": [],
    "user_choice": None,
    "approval_prompted": False,
    "open_question_protocol_resolved": False,
    "delegation_claimed": False,
    "dispatch_payload_keys": [],
    "phase_execution_started": False,
    "suppressed_action_ids": [],
    "tool_calls": {"runSubagent": 0},
    "presend": {"executed": True, "result": "pass", "failed_check": None},
    "output_paths": [],
}

BASE_BLACKBOARD: dict[str, Any] = {
    "row_present": True,
    "row_schema_valid": True,
    "row_id": "BBR-000001",
    "session_id": "sess-001",
    "workflow_id": "wf-001",
    "predecessor_workflow_id": None,
    "successor_workflow_id": None,
    "item_id": "item-001",
    "lifecycle_stage": "route",
    "workflow_lifecycle": "non_terminal_active",
    "fsm_state_ref": "ST-010",
    "prior_non_terminal_fsm_state": None,
    "owner_lock": {
        "active": "ARTHUR",
        "lock_token": "tok-001",
        "acquired_at": "2026-05-31T10:00:00Z",
        "expires_at": "2026-12-31T00:00:00Z",
        "is_stale": False,
        "active_lock_count": 1,
    },
    "gates": {
        "BG-001": "pass",
        "BG-002": "pass",
        "BG-003": "pass",
        "BG-004": "pass",
        "BG-005": "pass",
        "BG-006": "pass",
    },
    "required_gates_passed": True,
    "terminal": {
        "is_terminal": False,
        "terminal_state": None,
        "terminalized_at": None,
        "terminal_reason": None,
    },
    "audit": {
        "created_at": "2026-05-31T10:00:00Z",
        "created_by": "ARTHUR",
        "revision": 1,
        "immutable_fields_hash": "abc123",
        "audit_fields_mutated": False,
    },
    "mutation_attempt_keys": [],
}


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Merge overrides into base; one level of dict nesting is merged, not replaced."""
    result: dict[str, Any] = {}
    all_keys = set(base) | set(overrides)
    for key in all_keys:
        base_val = base.get(key)
        if key not in overrides:
            result[key] = base_val
        elif isinstance(base_val, dict) and isinstance(overrides[key], dict):
            result[key] = {**base_val, **overrides[key]}
        else:
            result[key] = overrides[key]
    return result


def _check_composite_identity(snap: Snapshot) -> str | None:
    """Return IDENTITY_COMPOSITE if session_id, workflow_id, or turn_id is absent."""
    if not snap.session_id or not snap.workflow_id or not snap.turn_id:
        return "IDENTITY_COMPOSITE"
    return None


@dataclass(frozen=True)
class TurnResult:
    turn_index: int
    passed: bool
    failed_check: str | None
    state_after: str | None


@dataclass(frozen=True)
class TCResult:
    tc_id: str
    verdict: str
    failed_check: str | None
    state_after: str | None
    turns: tuple[TurnResult, ...]
    expected_verdict: str
    matched: bool
    mismatch_reason: str | None


def _evaluate_turn(
    snapshot_data: dict[str, Any],
    blackboard_data: dict[str, Any] | None,
) -> TurnResult:
    """Evaluate one turn: identity → BG gates → invariants → presend."""
    snap = Snapshot.from_dict(snapshot_data)

    identity_fail = _check_composite_identity(snap)
    if identity_fail is not None:
        return TurnResult(
            turn_index=0, passed=False, failed_check=identity_fail, state_after=None
        )

    bb: BlackboardRow | None = None
    if blackboard_data is not None:
        bb = BlackboardRow.from_dict(blackboard_data)

    if bb is not None:
        bg = evaluate_blackboard_gates(snap, bb, now=_NOW)
        if not bg.passed:
            return TurnResult(
                turn_index=0,
                passed=False,
                failed_check=bg.first_failure_id,
                state_after=bg.decision.state_after if bg.decision else None,
            )
        inv = evaluate_invariants(snap, bb, _REGISTRY.resolve_role)
        if not inv.passed:
            return TurnResult(
                turn_index=0,
                passed=False,
                failed_check=inv.first_failure_id,
                state_after=None,
            )

    ps = run_presend_checks(snap)
    if not ps.passed:
        return TurnResult(
            turn_index=0,
            passed=False,
            failed_check=ps.failed_check,
            state_after=ps.decision.state_after if ps.decision else None,
        )

    return TurnResult(
        turn_index=0, passed=True, failed_check=None, state_after=snap.state_after
    )


def replay_tc(tc: dict[str, Any]) -> TCResult:
    """Replay all turns of one TC fixture and compare to expected verdict."""
    tc_id = str(tc.get("tc_id", "?"))
    expected_verdict = str(tc.get("expected_verdict", "PASS"))
    expected_failed_check = tc.get("expected_failed_check")
    turns_data: list[dict[str, Any]] = tc.get("turns", [])

    turn_results: list[TurnResult] = []
    first_failure: TurnResult | None = None

    for i, turn in enumerate(turns_data):
        snap_overrides = turn.get("snapshot_overrides", {})
        bb_overrides = turn.get("blackboard_overrides")

        snap_data = _deep_merge(BASE_SNAPSHOT, snap_overrides)
        bb_data = _deep_merge(BASE_BLACKBOARD, bb_overrides) if bb_overrides is not None else None

        result = _evaluate_turn(snap_data, bb_data)
        tr = TurnResult(
            turn_index=i,
            passed=result.passed,
            failed_check=result.failed_check,
            state_after=result.state_after,
        )
        turn_results.append(tr)
        if not tr.passed and first_failure is None:
            first_failure = tr

    verdict = "FAIL" if first_failure else "PASS"
    failed_check = first_failure.failed_check if first_failure else None
    state_after = (
        first_failure.state_after
        if first_failure
        else (turn_results[-1].state_after if turn_results else None)
    )

    matched = verdict == expected_verdict and (
        expected_failed_check is None or failed_check == expected_failed_check
    )
    mismatch_reason = (
        None
        if matched
        else (
            f"expected verdict={expected_verdict} failed_check={expected_failed_check}; "
            f"got verdict={verdict} failed_check={failed_check}"
        )
    )

    return TCResult(
        tc_id=tc_id,
        verdict=verdict,
        failed_check=failed_check,
        state_after=state_after,
        turns=tuple(turn_results),
        expected_verdict=expected_verdict,
        matched=matched,
        mismatch_reason=mismatch_reason,
    )
