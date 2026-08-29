"""BG-001..BG-006 ascending fail-fast gate evaluator — POL-054 (spec015 Task 6.1).

Evaluates the hard quality gates in strict ascending BG order. On the first
failing gate, evaluation stops (fail-fast) — every later gate is recorded as
``not_evaluated`` (never ``pass``/``fail``), so a downstream gate is provably
not evaluated once an earlier one fails. The first failure's deterministic
§11.3 "Blocked Behavior" is applied: the suppressed action ids, the ST-903
correction reroute (only when the turn is non-terminal), and the BG-006 terminal
mutation rejection.

Pure functional: results are computed from ``snapshot`` + ``blackboard`` + the
evaluation ``now``; the store is never mutated.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from helm_controller.contracts.blackboard import BlackboardRow
from helm_controller.contracts.decision import Decision
from helm_controller.contracts.snapshot import Snapshot
from helm_controller.fsm.states import TERMINAL_STATE_IDS, State
from helm_controller.gates.bg_rules import (
    BEHAVIOR,
    BG_ORDER,
    FAIL_REASON,
    PREDICATES,
    GateOutcome,
    GateStatus,
)

PRE_SEND_BLOCKED_STATE = State.PRE_SEND_BLOCKED.value


@dataclass(frozen=True)
class BgEvaluation:
    """Aggregate result of evaluating BG-001..BG-006 for one turn."""

    passed: bool
    first_failure_id: str | None
    outcomes: tuple[GateOutcome, ...]
    suppressed_action_ids: tuple[str, ...]
    route_to_st903: bool
    mutation_rejected: bool
    required_gates_passed: bool
    decision: Decision | None


def evaluate_blackboard_gates(
    snapshot: Snapshot, blackboard: BlackboardRow, *, now: datetime
) -> BgEvaluation:
    """Evaluate the BG gate sequence ascending with fail-fast (POL-054)."""
    prior: dict[str, GateStatus] = {}
    outcomes: list[GateOutcome] = []
    failed_id: str | None = None

    for gate_id in BG_ORDER:
        passed = PREDICATES[gate_id](snapshot, blackboard, prior, now)
        if passed:
            prior[gate_id] = GateStatus.PASS
            outcomes.append(GateOutcome(gate_id, GateStatus.PASS, f"{gate_id} pass"))
            continue
        # No soft/`fail` branch by design: per spec §6.4 hard gates map to
        # BLOCKED and soft gates to `fail`, but BG-001..006 are all HARD gates,
        # so a failing BG gate is ALWAYS BLOCKED — there are no soft BG gates.
        prior[gate_id] = GateStatus.BLOCKED
        outcomes.append(
            GateOutcome(gate_id, GateStatus.BLOCKED, FAIL_REASON[gate_id])
        )
        failed_id = gate_id
        break

    for gate_id in BG_ORDER[len(outcomes):]:
        prior[gate_id] = GateStatus.NOT_EVALUATED
        outcomes.append(
            GateOutcome(
                gate_id,
                GateStatus.NOT_EVALUATED,
                "not evaluated (fail-fast)",
            )
        )

    if failed_id is None:
        return BgEvaluation(
            passed=True,
            first_failure_id=None,
            outcomes=tuple(outcomes),
            suppressed_action_ids=(),
            route_to_st903=False,
            mutation_rejected=False,
            required_gates_passed=True,
            decision=None,
        )

    behavior = BEHAVIOR[failed_id]
    terminal_before = snapshot.state_before in TERMINAL_STATE_IDS
    suppressed = tuple(a for a in snapshot.actions if a in behavior.suppress)
    route_to_st903 = behavior.routes_to_st903 and not terminal_before
    state_after = PRE_SEND_BLOCKED_STATE if route_to_st903 else snapshot.state_before
    decision = Decision(
        decision="deny",
        reason_id=failed_id,
        reason=f"{failed_id}: {FAIL_REASON[failed_id]}",
        state_after=state_after,
        suppressed_action_ids=list(suppressed) or None,
    )
    return BgEvaluation(
        passed=False,
        first_failure_id=failed_id,
        outcomes=tuple(outcomes),
        suppressed_action_ids=suppressed,
        route_to_st903=route_to_st903,
        mutation_rejected=behavior.rejects_mutation,
        required_gates_passed=False,
        decision=decision,
    )
