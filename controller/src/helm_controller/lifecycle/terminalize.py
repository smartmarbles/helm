"""Terminal-transition `boundary_event = terminalize` enforcement — POL-014B (Task 7.4).

Every FSM transition that produces a terminal ``state_after`` — TR-001 (→ST-901),
TR-025 (→ST-902), TR-028 (→ST-902), TR-030 (→ST-900), TR-032 (→ST-900) — MUST set
``boundary_event = terminalize`` in the runtime snapshot for that turn. A terminal
transition whose snapshot omits ``terminalize`` is a protocol violation (POL-014B).
This is the F-002 resolution: terminalize is now explicit, derived from the
transition id, not invented ad hoc.

The terminal-transition set is cross-checked against the canonical FSM table
(:data:`helm_controller.fsm.transitions.TRANSITIONS`) at import time so it cannot
drift from the FSM source of truth.
"""

from __future__ import annotations

from dataclasses import replace

from helm_controller.contracts.snapshot import Snapshot
from helm_controller.fsm.states import is_terminal, state_by_id
from helm_controller.fsm.transitions import transition_by_id
from helm_controller.lifecycle.legality import BoundaryEvent

TERMINALIZE_BOUNDARY_EVENT = BoundaryEvent.TERMINALIZE.value

# POL-014B terminal transitions. Frozen here for fast lookup; validated against
# the FSM table by :func:`_assert_terminal_set_matches_fsm` at import time.
TERMINAL_TRANSITIONS: frozenset[str] = frozenset(
    {"TR-001", "TR-025", "TR-028", "TR-030", "TR-032"}
)

# Terminal ST-### id → store `terminal_reason` enum value (schema CHECK on
# workflows.terminal_reason). ST-900 success, ST-901 user stop, ST-902 reject.
TERMINAL_REASON_BY_STATE: dict[str, str] = {
    "ST-900": "success",
    "ST-901": "stop",
    "ST-902": "reject",
}


class TerminalizeViolation(ValueError):
    """Raised when a terminal transition's snapshot omits ``terminalize`` (POL-014B)."""

    def __init__(self, transition_id: str, boundary_event: str | None) -> None:
        self.transition_id = transition_id
        self.boundary_event = boundary_event
        super().__init__(
            f"{transition_id} is a terminal transition but boundary_event is "
            f"{boundary_event!r}, not {TERMINALIZE_BOUNDARY_EVENT!r} (POL-014B)"
        )


def _assert_terminal_set_matches_fsm() -> None:
    """Fail fast if :data:`TERMINAL_TRANSITIONS` drifts from the FSM table."""
    for transition_id in TERMINAL_TRANSITIONS:
        transition = transition_by_id(transition_id)
        to_state = transition.to_state
        if to_state is None or not is_terminal(to_state):
            raise AssertionError(
                f"{transition_id} is declared terminal but the FSM table maps it "
                f"to {to_state!r}, which is not a terminal state"
            )


_assert_terminal_set_matches_fsm()


def is_terminal_transition(transition_id: str) -> bool:
    """Return ``True`` iff ``transition_id`` is one of the five POL-014B terminals."""
    return transition_id in TERMINAL_TRANSITIONS


def terminal_boundary_event(transition_id: str) -> str | None:
    """Return ``"terminalize"`` for a terminal transition, else ``None``."""
    if transition_id in TERMINAL_TRANSITIONS:
        return TERMINALIZE_BOUNDARY_EVENT
    return None


def enforce_terminalize(transition_id: str, snapshot: Snapshot) -> Snapshot:
    """Stamp ``boundary_event = terminalize`` on a terminal transition's snapshot.

    For a terminal transition, returns ``snapshot`` with ``boundary_event`` set to
    ``terminalize`` (idempotent if already set). For a non-terminal transition the
    snapshot is returned unchanged. Use this when emitting the per-turn snapshot so
    POL-014B can never be omitted.
    """
    if transition_id not in TERMINAL_TRANSITIONS:
        return snapshot
    if snapshot.boundary_event == TERMINALIZE_BOUNDARY_EVENT:
        return snapshot
    return replace(snapshot, boundary_event=TERMINALIZE_BOUNDARY_EVENT)


def assert_terminalize_present(transition_id: str, snapshot: Snapshot) -> None:
    """Raise :class:`TerminalizeViolation` if a terminal transition omits ``terminalize``.

    POL-014B protocol check for an already-emitted snapshot. Non-terminal
    transitions are never violations.
    """
    if transition_id not in TERMINAL_TRANSITIONS:
        return
    if snapshot.boundary_event != TERMINALIZE_BOUNDARY_EVENT:
        raise TerminalizeViolation(transition_id, snapshot.boundary_event)


def terminal_state_for(transition_id: str) -> str:
    """Return the canonical terminal ``ST-###`` id a terminal transition reaches.

    Read from the FSM table (never hard-coded) so it cannot drift. Raises
    :class:`TerminalizeViolation` if ``transition_id`` is not a terminal transition.
    """
    if transition_id not in TERMINAL_TRANSITIONS:
        raise TerminalizeViolation(transition_id, None)
    to_state = transition_by_id(transition_id).to_state
    # Guaranteed non-None terminal by _assert_terminal_set_matches_fsm at import.
    return state_by_id(to_state.value).value
