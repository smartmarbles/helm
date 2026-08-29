"""`prior_non_terminal_fsm_state` write/clear wiring — POL-014C (Task 7.3).

``prior_non_terminal_fsm_state`` is the AUTHORITATIVE record of the pre-interrupt
and pre-suspend FSM state (POL-014C). It MUST be written when entering an
interrupt (TR-002, → ST-090) or suspending (TR-033, → ST-000), and cleared when
returning from interrupt (TR-003) or resuming (TR-034). It MUST NEVER be derived
from any other snapshot field — the FSM's dynamic-destination transitions
(TR-003, TR-034) read this field as their sole source of truth.

This module computes the required mutation for a given transition; it does not
touch the store. The boundary evaluator (Task 7.2) consumes :func:`prior_state_mutation`
for the ``suspend`` (TR-033) and ``resume`` (TR-034) boundary events; the
interrupt transitions (TR-002 / TR-003) are FSM-internal and consume the same
helper through the Phase 8 pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# POL-014C: transitions that WRITE the field (interrupt entry, suspend).
WRITE_TRANSITIONS: frozenset[str] = frozenset({"TR-002", "TR-033"})
# POL-014C: transitions that CLEAR the field (interrupt return, resume).
CLEAR_TRANSITIONS: frozenset[str] = frozenset({"TR-003", "TR-034"})

PRIOR_STATE_COLUMN = "prior_non_terminal_fsm_state"


class PriorStateAction(Enum):
    """What a transition does to ``prior_non_terminal_fsm_state``."""

    WRITE = "write"
    CLEAR = "clear"
    NOOP = "noop"


@dataclass(frozen=True)
class PriorStateMutation:
    """The required ``prior_non_terminal_fsm_state`` change for a transition."""

    action: PriorStateAction
    value: str | None

    @property
    def mutates(self) -> bool:
        """``True`` iff this transition writes or clears the field."""
        return self.action is not PriorStateAction.NOOP

    def as_field_update(self) -> dict[str, str | None]:
        """The ``workflow_fields`` fragment to apply, or ``{}`` for a no-op."""
        if self.action is PriorStateAction.NOOP:
            return {}
        return {PRIOR_STATE_COLUMN: self.value}


def prior_state_mutation(
    transition_id: str, *, pre_transition_state: str | None
) -> PriorStateMutation:
    """Return the POL-014C mutation for ``transition_id``.

    For a WRITE transition (TR-002, TR-033) the field is set to
    ``pre_transition_state`` — the authoritative non-terminal FSM state the
    workflow occupied immediately before the interrupt/suspend. A WRITE with no
    ``pre_transition_state`` is a programming error (there is no prior state to
    record) and raises :class:`ValueError`. For a CLEAR transition (TR-003,
    TR-034) the field is set to ``None``. Every other transition is a no-op.
    """
    if transition_id in WRITE_TRANSITIONS:
        if pre_transition_state is None:
            raise ValueError(
                f"{transition_id} writes {PRIOR_STATE_COLUMN} but "
                "pre_transition_state is None"
            )
        return PriorStateMutation(PriorStateAction.WRITE, pre_transition_state)
    if transition_id in CLEAR_TRANSITIONS:
        return PriorStateMutation(PriorStateAction.CLEAR, None)
    return PriorStateMutation(PriorStateAction.NOOP, None)
