"""Direct static-data tests for the FSM engine (spec015 Task 5.5).

Covers static data and lookups that active transition paths do not reach:
every enum member accessed by value and by name, every ``*_by_id`` lookup
exercised for both found and not-found branches, terminal/non-terminal
partitioning, descriptions, and the dynamic-destination property.
"""

from __future__ import annotations

import pytest

from helm_controller.fsm.actions import (
    Action,
    UnknownActionError,
    action_by_id,
)
from helm_controller.fsm.events import Event, UnknownEventError, event_by_id
from helm_controller.fsm.guards import Guard, UnknownGuardError, guard_by_id
from helm_controller.fsm.states import (
    NON_TERMINAL_STATES,
    TERMINAL_STATES,
    State,
    UnknownStateError,
    description,
    is_terminal,
    state_by_id,
)
from helm_controller.fsm.transitions import (
    TRANSITIONS,
    UnknownTransitionError,
    transition_by_id,
)


# ---------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------


def test_state_access_by_value_and_name() -> None:
    for member in State:
        assert State(member.value) is member
        assert State[member.name] is member


def test_state_by_id_found() -> None:
    assert state_by_id("ST-000") is State.IDLE


def test_state_by_id_not_found() -> None:
    with pytest.raises(UnknownStateError):
        state_by_id("ST-999")


def test_terminal_partition_is_complete_and_disjoint() -> None:
    assert set(TERMINAL_STATES) == {State.COMPLETED, State.STOPPED, State.REJECTED}
    assert set(NON_TERMINAL_STATES).isdisjoint(TERMINAL_STATES)
    assert set(NON_TERMINAL_STATES) | set(TERMINAL_STATES) == set(State)


def test_is_terminal_both_arms() -> None:
    assert is_terminal(State.COMPLETED) is True
    assert is_terminal(State.IDLE) is False


def test_description_present_for_every_state() -> None:
    for member in State:
        assert description(member)


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


def test_event_access_by_value_and_name() -> None:
    for member in Event:
        assert Event(member.value) is member
        assert Event[member.name] is member


def test_event_count_is_25() -> None:
    assert len(list(Event)) == 25


def test_event_by_id_found() -> None:
    assert event_by_id("EV-001") is Event.USER_WORK_REQUEST


def test_event_by_id_not_found() -> None:
    with pytest.raises(UnknownEventError):
        event_by_id("EV-999")


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def test_action_access_by_value_and_name() -> None:
    for member in Action:
        assert Action(member.value) is member
        assert Action[member.name] is member


def test_action_count_is_12() -> None:
    assert len(list(Action)) == 12


def test_action_by_id_found() -> None:
    assert action_by_id("AC-001") is Action.ROUTE_REQUEST


def test_action_by_id_not_found() -> None:
    with pytest.raises(UnknownActionError):
        action_by_id("AC-999")


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


def test_guard_access_by_value_and_name() -> None:
    for member in Guard:
        assert Guard(member.value) is member
        assert Guard[member.name] is member


def test_guard_count_is_15() -> None:
    assert len(list(Guard)) == 15


def test_guard_by_id_found() -> None:
    assert guard_by_id("GD-001") is Guard.GD_001


def test_guard_by_id_not_found() -> None:
    with pytest.raises(UnknownGuardError):
        guard_by_id("GD-999")


# ---------------------------------------------------------------------------
# Transitions
# ---------------------------------------------------------------------------


def test_transition_count_is_35() -> None:
    assert len(TRANSITIONS) == 35


def test_transition_ids_are_sequential() -> None:
    ids = [transition.transition_id for transition in TRANSITIONS]
    assert ids == [f"TR-{n:03d}" for n in range(1, 36)]


def test_transition_by_id_found() -> None:
    assert transition_by_id("TR-004").to_state is State.ROUTE_SELECTION


def test_transition_by_id_not_found() -> None:
    with pytest.raises(UnknownTransitionError):
        transition_by_id("TR-999")


def test_dynamic_destination_property_both_arms() -> None:
    assert transition_by_id("TR-003").dynamic_destination is True
    assert transition_by_id("TR-034").dynamic_destination is True
    assert transition_by_id("TR-004").dynamic_destination is False


def test_only_tr003_and_tr034_are_dynamic() -> None:
    dynamic = {t.transition_id for t in TRANSITIONS if t.dynamic_destination}
    assert dynamic == {"TR-003", "TR-034"}
