"""Tests for `prior_non_terminal_fsm_state` write/clear wiring — POL-014C (Task 7.5)."""

from __future__ import annotations

import pytest

from helm_controller.lifecycle.prior_state import (
    CLEAR_TRANSITIONS,
    PRIOR_STATE_COLUMN,
    PriorStateAction,
    WRITE_TRANSITIONS,
    prior_state_mutation,
)


def test_write_transitions_are_tr002_and_tr033() -> None:
    assert WRITE_TRANSITIONS == frozenset({"TR-002", "TR-033"})


def test_clear_transitions_are_tr003_and_tr034() -> None:
    assert CLEAR_TRANSITIONS == frozenset({"TR-003", "TR-034"})


@pytest.mark.parametrize("transition_id", ["TR-002", "TR-033"])
def test_write_transition_records_pre_state(transition_id: str) -> None:
    mutation = prior_state_mutation(transition_id, pre_transition_state="ST-080")
    assert mutation.action is PriorStateAction.WRITE
    assert mutation.value == "ST-080"
    assert mutation.mutates is True
    assert mutation.as_field_update() == {PRIOR_STATE_COLUMN: "ST-080"}


@pytest.mark.parametrize("transition_id", ["TR-002", "TR-033"])
def test_write_transition_without_pre_state_raises(transition_id: str) -> None:
    with pytest.raises(ValueError, match="pre_transition_state is None"):
        prior_state_mutation(transition_id, pre_transition_state=None)


@pytest.mark.parametrize("transition_id", ["TR-003", "TR-034"])
def test_clear_transition_sets_field_null(transition_id: str) -> None:
    mutation = prior_state_mutation(transition_id, pre_transition_state="ST-080")
    assert mutation.action is PriorStateAction.CLEAR
    assert mutation.value is None
    assert mutation.mutates is True
    assert mutation.as_field_update() == {PRIOR_STATE_COLUMN: None}


@pytest.mark.parametrize("transition_id", ["TR-001", "TR-004", "TR-030"])
def test_unrelated_transition_is_noop(transition_id: str) -> None:
    mutation = prior_state_mutation(transition_id, pre_transition_state="ST-080")
    assert mutation.action is PriorStateAction.NOOP
    assert mutation.value is None
    assert mutation.mutates is False
    assert mutation.as_field_update() == {}
