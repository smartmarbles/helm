"""INV-001..INV-021 invariant evaluator — POL-045 (spec015 Task 6.3).

Evaluates every machine-checkable invariant for one turn. Invariants are not
ordered fail-fast like the BG gates or CHK checks — every invariant is checked
and all violations are collected — but the deterministic ``first_failure_id``
(lowest INV id, by §8 table order) is reported for the decision reason id, per
POL-045 ("any false invariant evaluation is an immediate policy FAIL").

Pure functional: computed from ``snapshot`` + ``blackboard`` + the role
resolver; the store is never mutated.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from helm_controller.contracts.blackboard import BlackboardRow
from helm_controller.contracts.decision import Decision
from helm_controller.contracts.snapshot import Snapshot
from helm_controller.invariants.inv_rules import INV_ORDER, PREDICATES, REASON


@dataclass(frozen=True)
class InvariantViolation:
    """A single failed invariant."""

    invariant_id: str
    reason: str


@dataclass(frozen=True)
class InvariantEvaluation:
    """Aggregate result of evaluating INV-001..INV-021 for one turn."""

    passed: bool
    first_failure_id: str | None
    violations: tuple[InvariantViolation, ...]
    decision: Decision | None


def evaluate_invariants(
    snapshot: Snapshot,
    blackboard: BlackboardRow,
    resolve_role: Callable[[str], str],
) -> InvariantEvaluation:
    """Evaluate all invariants; report the lowest-id violation (POL-045)."""
    violations: list[InvariantViolation] = []
    for inv_id in INV_ORDER:
        if not PREDICATES[inv_id](snapshot, blackboard, resolve_role):
            violations.append(InvariantViolation(inv_id, REASON[inv_id]))

    if not violations:
        return InvariantEvaluation(
            passed=True,
            first_failure_id=None,
            violations=(),
            decision=None,
        )

    first = violations[0]
    decision = Decision(
        decision="deny",
        reason_id=first.invariant_id,
        reason=f"{first.invariant_id}: {first.reason}",
    )
    return InvariantEvaluation(
        passed=False,
        first_failure_id=first.invariant_id,
        violations=tuple(violations),
        decision=decision,
    )
