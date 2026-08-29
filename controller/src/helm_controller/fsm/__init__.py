"""FSM engine — canonical state machine deciding transition legality (spec015 Phase 5).

Pure functional layer over the contracts and runtime store: immutable static
data (states, events, guards, actions, transitions), the transition evaluator,
and the POL-004 §4 action-matrix legality check (CHK-003).
"""

from __future__ import annotations

from helm_controller.fsm.action_matrix import (
    Chk003Result,
    Legality,
    check_action_matrix,
    is_allowed,
)
from helm_controller.fsm.actions import Action, UnknownActionError, action_by_id
from helm_controller.fsm.evaluator import TransitionResult, evaluate
from helm_controller.fsm.events import Event, UnknownEventError, event_by_id
from helm_controller.fsm.guards import (
    Guard,
    UnknownGuardError,
    evaluate_guard,
    guard_by_id,
)
from helm_controller.fsm.states import (
    NON_TERMINAL_STATES,
    TERMINAL_STATES,
    State,
    UnknownStateError,
    is_terminal,
    state_by_id,
)
from helm_controller.fsm.transitions import (
    TRANSITIONS,
    Transition,
    UnknownTransitionError,
    transition_by_id,
)

__all__ = [
    "Action",
    "Chk003Result",
    "Event",
    "Guard",
    "Legality",
    "NON_TERMINAL_STATES",
    "State",
    "TERMINAL_STATES",
    "TRANSITIONS",
    "Transition",
    "TransitionResult",
    "UnknownActionError",
    "UnknownEventError",
    "UnknownGuardError",
    "UnknownStateError",
    "UnknownTransitionError",
    "action_by_id",
    "check_action_matrix",
    "evaluate",
    "evaluate_guard",
    "event_by_id",
    "guard_by_id",
    "is_allowed",
    "is_terminal",
    "state_by_id",
    "transition_by_id",
]
