"""BG-001..BG-006 hard-gate rule data and pass predicates — POL-054
(spec015 Task 6.1).

Transcribed faithfully from the normative source
``artifacts/docs/orchestration-fsm-policy-and-test-matrix.md`` §11.3 ("Hard
Quality Gates"). Each gate has a pure pass predicate over the per-turn snapshot,
the blackboard row, the prior gates' computed statuses (BG-004/BG-005 depend on
BG-001..BG-003), and the evaluation ``now`` (BG-003 lock-expiry). The
deterministic "Blocked Behavior" column is modelled as :class:`BlockedBehavior`
and applied by :mod:`helm_controller.gates.bg_evaluator`.

The predicate functions are public so the inner branches that ascending
fail-fast ordering can never reach in the evaluator (e.g. BG-004 with a failed
prior gate) can be exercised directly for full branch coverage.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType

from helm_controller.contracts.blackboard import BlackboardRow
from helm_controller.contracts.snapshot import Snapshot
from helm_controller.gates.stage_state_map import allowed_states

DISPATCH_ACTION = "AC-002"
EXECUTE_ACTION = "AC-006"
EXECUTE_PHASES_STATE = "ST-080"

BG_ORDER: tuple[str, ...] = (
    "BG-001",
    "BG-002",
    "BG-003",
    "BG-004",
    "BG-005",
    "BG-006",
)


class GateStatus(Enum):
    """Per-gate status (mirrors the contract ``gateStatus`` enum)."""

    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    NOT_EVALUATED = "not_evaluated"


@dataclass(frozen=True)
class GateOutcome:
    """The computed status and reason for a single BG gate on one turn."""

    gate_id: str
    status: GateStatus
    reason: str


@dataclass(frozen=True)
class BlockedBehavior:
    """The deterministic §11.3 consequence applied when a gate fails.

    ``suppress`` is the set of action ids blocked when present in the turn.
    ``routes_to_st903`` requests the ST-903 correction reroute (the evaluator
    additionally gates this on the turn being non-terminal). ``rejects_mutation``
    marks the BG-006 terminal-row mutation rejection (state stays terminal).
    """

    suppress: frozenset[str]
    routes_to_st903: bool
    rejects_mutation: bool


# §11.3 "Blocked Behavior (Deterministic)" column.
BEHAVIOR: "MappingProxyType[str, BlockedBehavior]" = MappingProxyType(
    {
        "BG-001": BlockedBehavior(
            frozenset({DISPATCH_ACTION, EXECUTE_ACTION}), True, False
        ),
        "BG-002": BlockedBehavior(
            frozenset({DISPATCH_ACTION, EXECUTE_ACTION}), True, False
        ),
        "BG-003": BlockedBehavior(
            frozenset({DISPATCH_ACTION, EXECUTE_ACTION}), True, False
        ),
        "BG-004": BlockedBehavior(frozenset({DISPATCH_ACTION}), True, False),
        "BG-005": BlockedBehavior(frozenset({EXECUTE_ACTION}), True, False),
        "BG-006": BlockedBehavior(frozenset(), False, True),
    }
)

# Human-readable failure reasons for each gate (audit payload).
FAIL_REASON: "MappingProxyType[str, str]" = MappingProxyType(
    {
        "BG-001": "blackboard row absent or schema-invalid",
        "BG-002": "fsm_state_ref / lifecycle_stage inconsistent with state_before",
        "BG-003": "owner lock invalid, stale, expired, or count mismatch",
        "BG-004": "dispatch attempted while a precondition gate is unsatisfied",
        "BG-005": "execution entry attempted while preconditions unsatisfied",
        "BG-006": "mutation attempted on a terminal blackboard row",
    }
)


def _parse_iso(value: str) -> datetime:
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _not_expired(expires_at: str | None, now: datetime) -> bool:
    if expires_at is None:
        return False
    return _parse_iso(expires_at) >= now


def bg_001(
    snapshot: Snapshot,
    blackboard: BlackboardRow,
    prior: dict[str, GateStatus],
    now: datetime,
) -> bool:
    """BG-001: ``row_present == true AND row_schema_valid == true``."""
    return all((blackboard.row_present, blackboard.row_schema_valid))


def bg_002(
    snapshot: Snapshot,
    blackboard: BlackboardRow,
    prior: dict[str, GateStatus],
    now: datetime,
) -> bool:
    """BG-002: ``fsm_state_ref == state_before AND
    stage_state_map[lifecycle_stage] contains state_before``."""
    states = allowed_states(blackboard.lifecycle_stage)
    return all(
        (
            blackboard.fsm_state_ref == snapshot.state_before,
            states is not None and snapshot.state_before in states,
        )
    )


def bg_003(
    snapshot: Snapshot,
    blackboard: BlackboardRow,
    prior: dict[str, GateStatus],
    now: datetime,
) -> bool:
    """BG-003: active-lock-live disjunct OR no-lock (suspended/terminal) disjunct."""
    lock = blackboard.owner_lock
    active_ok = all(
        (
            blackboard.workflow_lifecycle == "non_terminal_active",
            lock.active_lock_count == 1,
            lock.is_stale is False,
            _not_expired(lock.expires_at, now),
        )
    )
    idle_ok = all(
        (
            blackboard.workflow_lifecycle in {"non_terminal_suspended", "terminal"},
            lock.active_lock_count == 0,
            lock.active is None,
        )
    )
    return active_ok or idle_ok


def bg_004(
    snapshot: Snapshot,
    blackboard: BlackboardRow,
    prior: dict[str, GateStatus],
    now: datetime,
) -> bool:
    """BG-004: ``AC-002 not in actions OR (BG-001..BG-003 all pass)``."""
    if DISPATCH_ACTION not in snapshot.actions:
        return True
    return all(
        (
            prior.get("BG-001") is GateStatus.PASS,
            prior.get("BG-002") is GateStatus.PASS,
            prior.get("BG-003") is GateStatus.PASS,
        )
    )


def bg_005(
    snapshot: Snapshot,
    blackboard: BlackboardRow,
    prior: dict[str, GateStatus],
    now: datetime,
) -> bool:
    """BG-005: ``state_after != ST-080 OR (BG-001..BG-003 pass AND
    open_question_protocol_resolved)``."""
    if snapshot.state_after != EXECUTE_PHASES_STATE:
        return True
    return all(
        (
            prior.get("BG-001") is GateStatus.PASS,
            prior.get("BG-002") is GateStatus.PASS,
            prior.get("BG-003") is GateStatus.PASS,
            snapshot.open_question_protocol_resolved,
        )
    )


def bg_006(
    snapshot: Snapshot,
    blackboard: BlackboardRow,
    prior: dict[str, GateStatus],
    now: datetime,
) -> bool:
    """BG-006: ``terminal.is_terminal == false OR mutation_attempt_keys == []``."""
    return (
        not blackboard.terminal.is_terminal
        or len(blackboard.mutation_attempt_keys) == 0
    )


_Predicate = Callable[[Snapshot, BlackboardRow, dict[str, GateStatus], datetime], bool]

PREDICATES: "MappingProxyType[str, _Predicate]" = MappingProxyType(
    {
        "BG-001": bg_001,
        "BG-002": bg_002,
        "BG-003": bg_003,
        "BG-004": bg_004,
        "BG-005": bg_005,
        "BG-006": bg_006,
    }
)
