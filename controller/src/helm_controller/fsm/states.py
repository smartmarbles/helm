"""FSM states ST-000..ST-903 — immutable static data (spec015 Task 5.1).

Transcribed faithfully from the normative source
``artifacts/docs/orchestration-fsm-policy-and-test-matrix.md`` §2.1. Terminal
states per POL-011..POL-013 are ST-900 (success), ST-901 (user stop), and
ST-902 (user reject); every other state is non-terminal.
"""

from __future__ import annotations

from enum import Enum
from types import MappingProxyType


class State(Enum):
    """Orchestration FSM state. Enum value is the canonical ST-### id."""

    IDLE = "ST-000"
    ROUTE_SELECTION = "ST-010"
    PREPARE_DISPATCH = "ST-020"
    WAIT_SUBAGENT = "ST-030"
    WAIT_OPEN_QUESTION_CHOICE = "ST-040"
    CLARIFIER_OWNED = "ST-050"
    WAIT_SPEC_APPROVAL = "ST-060"
    WAIT_PLAN_APPROVAL = "ST-070"
    EXECUTE_PHASES = "ST-080"
    PROCESS_AUDIT = "ST-090"
    PRE_SEND_BLOCKED = "ST-903"
    COMPLETED = "ST-900"
    STOPPED = "ST-901"
    REJECTED = "ST-902"


class UnknownStateError(KeyError):
    """Raised when an ST-### id has no corresponding :class:`State` member."""


_DESCRIPTIONS = MappingProxyType(
    {
        State.IDLE: "No workflow is currently active for the session.",
        State.ROUTE_SELECTION: "Classify request and choose path.",
        State.PREPARE_DISPATCH: "Build compliant brief and run pre-send gate.",
        State.WAIT_SUBAGENT: "Await delegated result.",
        State.WAIT_OPEN_QUESTION_CHOICE: "Waiting for user choice: quiz/inline/defer.",
        State.CLARIFIER_OWNED: "clarifier owns question collection interaction.",
        State.WAIT_SPEC_APPROVAL: "Await explicit approve/revise/reject for spec.",
        State.WAIT_PLAN_APPROVAL: "Await explicit approve/revise/reject for plan.",
        State.EXECUTE_PHASES: "Execute approved plan phases.",
        State.PROCESS_AUDIT: "Handle process-audit/meta question interrupt.",
        State.PRE_SEND_BLOCKED: "Pre-send gate failed; corrective action required.",
        State.COMPLETED: "Workflow completed successfully.",
        State.STOPPED: "Workflow terminated by user stop.",
        State.REJECTED: "Workflow terminated by user reject.",
    }
)

TERMINAL_STATES: tuple[State, ...] = (State.COMPLETED, State.STOPPED, State.REJECTED)
NON_TERMINAL_STATES: tuple[State, ...] = tuple(
    state for state in State if state not in TERMINAL_STATES
)
TERMINAL_STATE_IDS: frozenset[str] = frozenset(state.value for state in TERMINAL_STATES)

_BY_ID = MappingProxyType({state.value: state for state in State})


def state_by_id(state_id: str) -> State:
    """Return the :class:`State` whose value is ``state_id``.

    Raises :class:`UnknownStateError` when no member matches.
    """
    if state_id not in _BY_ID:
        raise UnknownStateError(state_id)
    return _BY_ID[state_id]


def is_terminal(state: State) -> bool:
    """Return ``True`` iff ``state`` is one of ST-900/ST-901/ST-902."""
    return state in TERMINAL_STATES


def description(state: State) -> str:
    """Return the normative §2.1 description for ``state``."""
    return _DESCRIPTIONS[state]
