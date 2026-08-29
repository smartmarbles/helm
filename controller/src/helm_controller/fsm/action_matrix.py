"""Action-matrix legality check — POL-004 §4 Allowed/Forbidden matrix; CHK-003
(spec015 Task 5.4).

Transcribed faithfully from the normative source
``artifacts/docs/orchestration-fsm-policy-and-test-matrix.md`` §4. Each cell is
``Y`` (allowed), ``N`` (forbidden), or a conditional predicate over the snapshot
context (the §4 "Y (if …)" annotations). CHK-003 is satisfied when every
matrix-governed action in a turn is allowed in ``state_before``.

Matrix-governed actions are exactly the §4 columns: AC-001, AC-002, AC-003,
AC-004, AC-005, AC-006, AC-007, AC-008, and AC-012. The internal control actions
AC-009 (BLOCK_OUTBOUND_SEND), AC-010 (RESUME_PRE_INTERRUPT_STATE), and AC-011
(MARK_TERMINAL) are deliberately absent from §4 — their legality is governed by
CHK-001/CHK-002 action-shape predicates, not by this per-state matrix — so
CHK-003 treats them as exempt (not subject to the matrix).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from helm_controller.contracts.decision import Decision
from helm_controller.contracts.snapshot import Snapshot
from helm_controller.fsm.actions import Action
from helm_controller.fsm.states import State

CHK_003 = "CHK-003"
PRE_SEND_BLOCKED_STATE = State.PRE_SEND_BLOCKED.value

_GATE_DOCS = frozenset({"spec", "plan"})


class Legality(Enum):
    """Unconditional matrix cell verdict."""

    ALLOWED = "Y"
    FORBIDDEN = "N"


# --- Conditional cells (the §4 "Y (if …)" annotations) --------------------


def _allowed_if_open_questions(snapshot: Snapshot) -> bool:
    """ST-030 / AC-003: allowed only if EV-009 (open questions present)."""
    return snapshot.open_question_count > 0


def _allowed_if_no_questions_and_gate_doc(snapshot: Snapshot) -> bool:
    """ST-030 / AC-005: allowed only if EV-010 (no open questions) and gate doc."""
    return snapshot.open_question_count == 0 and snapshot.doc_type in _GATE_DOCS


def _allowed_if_quiz_or_inline(snapshot: Snapshot) -> bool:
    """ST-040 / AC-004: allowed only for EV-011 / EV-012."""
    return snapshot.event in {"EV-011", "EV-012"}


def _allowed_if_defer_and_gate_doc(snapshot: Snapshot) -> bool:
    """ST-040 / AC-005: allowed only for EV-013 (defer) and gate doc."""
    return snapshot.event == "EV-013" and snapshot.doc_type in _GATE_DOCS


def _allowed_if_revise(snapshot: Snapshot) -> bool:
    """ST-060 / ST-070 AC-002: dispatch allowed for revise (EV-016) only."""
    return snapshot.event == "EV-016"


def _allowed_if_approved(snapshot: Snapshot) -> bool:
    """ST-070 / AC-006: execute phase allowed only after approve (EV-015)."""
    return snapshot.event == "EV-015"


Cell = Legality | Callable[[Snapshot], bool]

_A = Legality.ALLOWED
_N = Legality.FORBIDDEN

# Column order mirrors §4: AC-001, AC-002, AC-003, AC-004, AC-005, AC-006,
# AC-007, AC-008, AC-012.
GOVERNED_ACTIONS: tuple[Action, ...] = (
    Action.ROUTE_REQUEST,
    Action.DISPATCH_SUBAGENT,
    Action.PROMPT_OPEN_QUESTION_OPTIONS,
    Action.INVOKE_CLARIFIER,
    Action.PROMPT_APPROVAL,
    Action.EXECUTE_PHASE,
    Action.RESPOND_PROCESS_AUDIT,
    Action.ACK_STOP,
    Action.DIRECT_DELIVERABLE_BY_ORCHESTRATOR,
)

EXEMPT_CONTROL_ACTIONS: frozenset[Action] = frozenset(
    {
        Action.BLOCK_OUTBOUND_SEND,
        Action.RESUME_PRE_INTERRUPT_STATE,
        Action.MARK_TERMINAL,
    }
)


def _row(
    ac001: Cell, ac002: Cell, ac003: Cell, ac004: Cell, ac005: Cell,
    ac006: Cell, ac007: Cell, ac008: Cell, ac012: Cell,
) -> "MappingProxyType[Action, Cell]":
    return MappingProxyType(
        {
            Action.ROUTE_REQUEST: ac001,
            Action.DISPATCH_SUBAGENT: ac002,
            Action.PROMPT_OPEN_QUESTION_OPTIONS: ac003,
            Action.INVOKE_CLARIFIER: ac004,
            Action.PROMPT_APPROVAL: ac005,
            Action.EXECUTE_PHASE: ac006,
            Action.RESPOND_PROCESS_AUDIT: ac007,
            Action.ACK_STOP: ac008,
            Action.DIRECT_DELIVERABLE_BY_ORCHESTRATOR: ac012,
        }
    )


MATRIX: "MappingProxyType[State, MappingProxyType[Action, Cell]]" = MappingProxyType(
    {
        #          AC-001 AC-002                  AC-003                          AC-004                    AC-005                                 AC-006              AC-007 AC-008 AC-012
        State.IDLE: _row(_N, _N, _N, _N, _N, _N, _N, _A, _N),
        State.ROUTE_SELECTION: _row(_A, _N, _N, _N, _N, _N, _N, _A, _N),
        State.PREPARE_DISPATCH: _row(_N, _A, _N, _N, _N, _N, _N, _A, _N),
        State.WAIT_SUBAGENT: _row(
            _N, _N, _allowed_if_open_questions, _N,
            _allowed_if_no_questions_and_gate_doc, _N, _N, _A, _N,
        ),
        State.WAIT_OPEN_QUESTION_CHOICE: _row(
            _N, _N, _N, _allowed_if_quiz_or_inline,
            _allowed_if_defer_and_gate_doc, _N, _N, _A, _N,
        ),
        State.CLARIFIER_OWNED: _row(_N, _N, _N, _N, _N, _N, _N, _A, _N),
        State.WAIT_SPEC_APPROVAL: _row(
            _N, _allowed_if_revise, _N, _N, _A, _N, _N, _A, _N,
        ),
        State.WAIT_PLAN_APPROVAL: _row(
            _N, _allowed_if_revise, _N, _N, _A, _allowed_if_approved, _N, _A, _N,
        ),
        State.EXECUTE_PHASES: _row(_N, _A, _N, _N, _N, _A, _N, _A, _N),
        State.PROCESS_AUDIT: _row(_N, _N, _N, _N, _N, _N, _A, _A, _N),
        State.PRE_SEND_BLOCKED: _row(_N, _N, _N, _N, _N, _N, _N, _A, _N),
        State.COMPLETED: _row(_N, _N, _N, _N, _N, _N, _N, _N, _N),
        State.STOPPED: _row(_N, _N, _N, _N, _N, _N, _N, _N, _N),
        State.REJECTED: _row(_N, _N, _N, _N, _N, _N, _N, _N, _N),
    }
)


@dataclass(frozen=True)
class Chk003Result:
    """Outcome of the CHK-003 action-matrix legality check."""

    passed: bool
    failed_action: str | None
    decision: Decision | None


def is_allowed(state: State, action: Action, snapshot: Snapshot) -> bool:
    """Return whether ``action`` is allowed in ``state`` under ``snapshot``.

    Precondition: ``action`` is a matrix-governed action
    (:data:`GOVERNED_ACTIONS`).
    """
    cell = MATRIX[state][action]
    if cell is Legality.ALLOWED:
        return True
    if cell is Legality.FORBIDDEN:
        return False
    return cell(snapshot)


def check_action_matrix(
    state: State, actions: Sequence[Action], snapshot: Snapshot
) -> Chk003Result:
    """Evaluate CHK-003 for ``actions`` in ``state``.

    Returns a passing result when every matrix-governed action is allowed.
    Exempt control actions (:data:`EXEMPT_CONTROL_ACTIONS`) are skipped. On the
    first forbidden action a failing result carrying the canonical CHK-003 deny
    (routed to ST-903) is returned.
    """
    for action in actions:
        if action in EXEMPT_CONTROL_ACTIONS:
            continue
        if not is_allowed(state, action, snapshot):
            decision = Decision(
                decision="deny",
                reason_id=CHK_003,
                reason=f"action {action.value} forbidden in {state.value}",
                state_after=PRE_SEND_BLOCKED_STATE,
            )
            return Chk003Result(
                passed=False, failed_action=action.value, decision=decision
            )
    return Chk003Result(passed=True, failed_action=None, decision=None)
