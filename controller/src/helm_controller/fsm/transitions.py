"""FSM transition table TR-001..TR-035 — immutable static data (spec015 Task 5.2).

Transcribed faithfully from the normative source
``artifacts/docs/orchestration-fsm-policy-and-test-matrix.md`` §2.5. Each
:class:`Transition` is an immutable ``(from-states, event, guards, actions,
to-state)`` tuple.

Modeling notes (representation of the normative table — no new FSM semantics):

* "Any non-terminal" source is expanded to :data:`states.NON_TERMINAL_STATES`;
  the terminal source set (ST-900/ST-901/ST-902) to :data:`states.TERMINAL_STATES`.
* The compound-event rows TR-009..TR-014 list a primary discrete event
  (EV-006/EV-007/EV-008) plus the co-event EV-009/EV-010. EV-009/EV-010 are, by
  the §2.2/§2.3 definitions, identical to guards GD-005/GD-006, which those same
  rows already carry — so the co-event is encoded through the guard and the
  ``event`` field holds the primary discrete event (the value a per-turn
  snapshot's single ``event`` field would carry).
* TR-003 and TR-034 have a dynamic destination resolved at evaluation time to the
  snapshot's ``prior_non_terminal_fsm_state`` (POL-014C). They are encoded with
  ``to_state=None``; :attr:`Transition.dynamic_destination` reports this.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from helm_controller.fsm.actions import Action
from helm_controller.fsm.events import Event
from helm_controller.fsm.guards import Guard
from helm_controller.fsm.states import (
    NON_TERMINAL_STATES,
    TERMINAL_STATES,
    State,
)


@dataclass(frozen=True)
class Transition:
    """An immutable FSM transition row from §2.5."""

    transition_id: str
    from_states: tuple[State, ...]
    event: Event
    guards: tuple[Guard, ...]
    actions: tuple[Action, ...]
    to_state: State | None

    @property
    def dynamic_destination(self) -> bool:
        """``True`` iff the destination resolves to ``prior_non_terminal_fsm_state``."""
        return self.to_state is None


class UnknownTransitionError(KeyError):
    """Raised when a TR-### id has no corresponding :class:`Transition`."""


TRANSITIONS: tuple[Transition, ...] = (
    Transition("TR-001", NON_TERMINAL_STATES, Event.USER_STOP, (Guard.GD_009,),
               (Action.ACK_STOP, Action.MARK_TERMINAL), State.STOPPED),
    Transition("TR-002", NON_TERMINAL_STATES, Event.USER_PROCESS_AUDIT_OR_META,
               (Guard.GD_009,), (Action.RESPOND_PROCESS_AUDIT,), State.PROCESS_AUDIT),
    Transition("TR-003", (State.PROCESS_AUDIT,), Event.AUDIT_RESPONSE_SENT, (),
               (Action.RESUME_PRE_INTERRUPT_STATE,), None),
    Transition("TR-004", (State.IDLE,), Event.USER_WORK_REQUEST, (),
               (Action.ROUTE_REQUEST,), State.ROUTE_SELECTION),
    Transition("TR-005", (State.ROUTE_SELECTION,), Event.PATH_SELECTED, (), (),
               State.PREPARE_DISPATCH),
    Transition("TR-006", (State.PREPARE_DISPATCH,), Event.PRE_SEND_PASS,
               (Guard.GD_010,), (Action.DISPATCH_SUBAGENT,), State.WAIT_SUBAGENT),
    Transition("TR-007", (State.PREPARE_DISPATCH,), Event.PRE_SEND_FAIL, (),
               (Action.BLOCK_OUTBOUND_SEND,), State.PRE_SEND_BLOCKED),
    Transition("TR-008", (State.PRE_SEND_BLOCKED,), Event.PRE_SEND_PASS,
               (Guard.GD_010,), (), State.PREPARE_DISPATCH),
    Transition("TR-009", (State.WAIT_SUBAGENT,), Event.SUBAGENT_RESULT_SPEC,
               (Guard.GD_002, Guard.GD_005), (Action.PROMPT_OPEN_QUESTION_OPTIONS,),
               State.WAIT_OPEN_QUESTION_CHOICE),
    Transition("TR-010", (State.WAIT_SUBAGENT,), Event.SUBAGENT_RESULT_PLAN,
               (Guard.GD_003, Guard.GD_005), (Action.PROMPT_OPEN_QUESTION_OPTIONS,),
               State.WAIT_OPEN_QUESTION_CHOICE),
    Transition("TR-011", (State.WAIT_SUBAGENT,), Event.SUBAGENT_RESULT_NON_GATE_DOC,
               (Guard.GD_004, Guard.GD_005), (Action.PROMPT_OPEN_QUESTION_OPTIONS,),
               State.WAIT_OPEN_QUESTION_CHOICE),
    Transition("TR-012", (State.WAIT_SUBAGENT,), Event.SUBAGENT_RESULT_SPEC,
               (Guard.GD_002, Guard.GD_006), (Action.PROMPT_APPROVAL,),
               State.WAIT_SPEC_APPROVAL),
    Transition("TR-013", (State.WAIT_SUBAGENT,), Event.SUBAGENT_RESULT_PLAN,
               (Guard.GD_003, Guard.GD_006), (Action.PROMPT_APPROVAL,),
               State.WAIT_PLAN_APPROVAL),
    Transition("TR-014", (State.WAIT_SUBAGENT,), Event.SUBAGENT_RESULT_NON_GATE_DOC,
               (Guard.GD_004, Guard.GD_006), (), State.PREPARE_DISPATCH),
    Transition("TR-015", (State.WAIT_OPEN_QUESTION_CHOICE,), Event.USER_CHOICE_QUIZ,
               (), (Action.INVOKE_CLARIFIER,), State.CLARIFIER_OWNED),
    Transition("TR-016", (State.WAIT_OPEN_QUESTION_CHOICE,), Event.USER_CHOICE_INLINE,
               (), (Action.INVOKE_CLARIFIER,), State.CLARIFIER_OWNED),
    Transition("TR-017", (State.WAIT_OPEN_QUESTION_CHOICE,), Event.USER_CHOICE_DEFER,
               (Guard.GD_002,), (Action.PROMPT_APPROVAL,), State.WAIT_SPEC_APPROVAL),
    Transition("TR-018", (State.WAIT_OPEN_QUESTION_CHOICE,), Event.USER_CHOICE_DEFER,
               (Guard.GD_003,), (Action.PROMPT_APPROVAL,), State.WAIT_PLAN_APPROVAL),
    Transition("TR-019", (State.WAIT_OPEN_QUESTION_CHOICE,), Event.USER_CHOICE_DEFER,
               (Guard.GD_004,), (), State.PREPARE_DISPATCH),
    Transition("TR-020", (State.CLARIFIER_OWNED,), Event.QUIZ_HANDOFF_COMPLETE,
               (Guard.GD_002,), (Action.PROMPT_APPROVAL,), State.WAIT_SPEC_APPROVAL),
    Transition("TR-021", (State.CLARIFIER_OWNED,), Event.QUIZ_HANDOFF_COMPLETE,
               (Guard.GD_003,), (Action.PROMPT_APPROVAL,), State.WAIT_PLAN_APPROVAL),
    Transition("TR-022", (State.CLARIFIER_OWNED,), Event.QUIZ_HANDOFF_COMPLETE,
               (Guard.GD_004,), (), State.PREPARE_DISPATCH),
    Transition("TR-023", (State.WAIT_SPEC_APPROVAL,), Event.USER_APPROVE, (), (),
               State.PREPARE_DISPATCH),
    Transition("TR-024", (State.WAIT_SPEC_APPROVAL,), Event.USER_REVISE, (), (),
               State.PREPARE_DISPATCH),
    Transition("TR-025", (State.WAIT_SPEC_APPROVAL,), Event.USER_REJECT, (),
               (Action.MARK_TERMINAL,), State.REJECTED),
    Transition("TR-026", (State.WAIT_PLAN_APPROVAL,), Event.USER_APPROVE, (), (),
               State.EXECUTE_PHASES),
    Transition("TR-027", (State.WAIT_PLAN_APPROVAL,), Event.USER_REVISE, (), (),
               State.PREPARE_DISPATCH),
    Transition("TR-028", (State.WAIT_PLAN_APPROVAL,), Event.USER_REJECT, (),
               (Action.MARK_TERMINAL,), State.REJECTED),
    Transition("TR-029", (State.EXECUTE_PHASES,), Event.PHASE_DONE_MORE, (),
               (Action.EXECUTE_PHASE,), State.EXECUTE_PHASES),
    Transition("TR-030", (State.EXECUTE_PHASES,), Event.PHASE_DONE_ALL, (),
               (Action.MARK_TERMINAL,), State.COMPLETED),
    Transition("TR-031", TERMINAL_STATES, Event.USER_WORK_REQUEST, (),
               (Action.ROUTE_REQUEST,), State.ROUTE_SELECTION),
    Transition("TR-032", (State.PREPARE_DISPATCH,), Event.WORKFLOW_COMPLETE, (),
               (Action.MARK_TERMINAL,), State.COMPLETED),
    Transition("TR-033", NON_TERMINAL_STATES, Event.USER_SUSPEND_WORKFLOW,
               (Guard.GD_011, Guard.GD_013), (), State.IDLE),
    Transition("TR-034", (State.IDLE,), Event.USER_RESUME_WORKFLOW,
               (Guard.GD_012, Guard.GD_014), (), None),
    Transition("TR-035", NON_TERMINAL_STATES, Event.USER_WORK_REQUEST,
               (Guard.GD_011, Guard.GD_013, Guard.GD_015),
               (Action.ROUTE_REQUEST, Action.MARK_TERMINAL), State.ROUTE_SELECTION),
)

_BY_ID = MappingProxyType({transition.transition_id: transition for transition in TRANSITIONS})


def transition_by_id(transition_id: str) -> Transition:
    """Return the :class:`Transition` whose id is ``transition_id``.

    Raises :class:`UnknownTransitionError` when no member matches.
    """
    if transition_id not in _BY_ID:
        raise UnknownTransitionError(transition_id)
    return _BY_ID[transition_id]
