"""FSM transition evaluator (spec015 Task 5.3).

Given ``(state_before, event, snapshot)`` this computes the matching transition
TR-### and validates its guards. When no legal transition exists it emits the
canonical illegal-transition failure (failure mode 1 per spec §6.4): deny the
triggering tool call, do not advance FSM state, route to ST-903 for correction.

This is a pure functional layer: it reads the snapshot context (including the
persisted ``prior_non_terminal_fsm_state`` that resolves TR-003/TR-034 dynamic
destinations) and returns a decision; it never mutates the store.

Reason ID: spec §6.4 designates failure mode 1 (illegal FSM transition) with the
lead check identifier ``CHK-003``; the same id is emitted whether the cause is a
forbidden action, an unsatisfied guard, or no matching transition.
"""

from __future__ import annotations

from dataclasses import dataclass

from helm_controller.contracts.decision import Decision
from helm_controller.contracts.snapshot import Snapshot
from helm_controller.fsm.events import Event
from helm_controller.fsm.guards import evaluate_guard
from helm_controller.fsm.states import State
from helm_controller.fsm.transitions import TRANSITIONS

ILLEGAL_TRANSITION_REASON_ID = "CHK-003"
PRE_SEND_BLOCKED_STATE = State.PRE_SEND_BLOCKED.value


@dataclass(frozen=True)
class TransitionResult:
    """Outcome of evaluating a transition request.

    On a legal transition ``legal`` is ``True`` and ``transition_id``,
    ``state_after`` and ``actions`` are populated. On an illegal transition
    ``legal`` is ``False`` and ``decision`` carries the canonical deny.
    """

    legal: bool
    transition_id: str | None
    state_after: str | None
    actions: tuple[str, ...]
    decision: Decision | None


def _illegal(state_before: State, event: Event, detail: str) -> TransitionResult:
    decision = Decision(
        decision="deny",
        reason_id=ILLEGAL_TRANSITION_REASON_ID,
        reason=(
            f"illegal FSM transition: {detail} "
            f"(state_before={state_before.value}, event={event.value})"
        ),
        state_after=PRE_SEND_BLOCKED_STATE,
    )
    return TransitionResult(
        legal=False,
        transition_id=None,
        state_after=PRE_SEND_BLOCKED_STATE,
        actions=(),
        decision=decision,
    )


def evaluate(state_before: State, event: Event, snapshot: Snapshot) -> TransitionResult:
    """Resolve the legal transition for ``(state_before, event)`` under ``snapshot``.

    Transitions are scanned in TR-### order; the first whose source set contains
    ``state_before``, whose event matches, and all of whose guards pass is
    selected. The §2.5 guard sets are mutually exclusive per ``(state, event)``,
    so first-match is the only match for a well-formed snapshot.
    """
    for transition in TRANSITIONS:
        if state_before not in transition.from_states:
            continue
        if event is not transition.event:
            continue
        if not all(evaluate_guard(guard, snapshot) for guard in transition.guards):
            continue
        destination = transition.to_state
        if destination is None:
            resolved = snapshot.prior_non_terminal_fsm_state
            if resolved is None:
                return _illegal(
                    state_before,
                    event,
                    "dynamic destination unresolved (prior_non_terminal_fsm_state is null)",
                )
            state_after = resolved
        else:
            state_after = destination.value
        return TransitionResult(
            legal=True,
            transition_id=transition.transition_id,
            state_after=state_after,
            actions=tuple(action.value for action in transition.actions),
            decision=None,
        )
    return _illegal(state_before, event, "no matching transition")
