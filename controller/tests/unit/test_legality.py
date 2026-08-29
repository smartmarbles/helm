"""Direct tests for the §4.4 boundary-event legality matrix (Task 7.5).

Exercises every (source-lifecycle x boundary-event) cell for both legal and
illegal outcomes, verifies the required state-mutation side effects for each
legal cell, and the unknown-event-type fallback branch. The fallback is tested
here (not via the evaluator) because the evaluator's own control flow only ever
passes valid enum members.
"""

from __future__ import annotations

import itertools

import pytest

from helm_controller.lifecycle.legality import (
    LIFECYCLE_ACTIVE,
    LIFECYCLE_SUSPENDED,
    LIFECYCLE_TERMINAL,
    BoundaryEvent,
    SourceLifecycle,
    StateMutation,
    evaluate_legality,
    is_legal,
)

# The 8 legal cells of the §4.4 matrix (event, source).
_LEGAL_CELLS = {
    (BoundaryEvent.NEW, SourceLifecycle.NONE),
    (BoundaryEvent.NEW, SourceLifecycle.TERMINAL),
    (BoundaryEvent.SUPERSEDE, SourceLifecycle.NON_TERMINAL_ACTIVE),
    (BoundaryEvent.SUPERSEDE, SourceLifecycle.NON_TERMINAL_SUSPENDED),
    (BoundaryEvent.SUSPEND, SourceLifecycle.NON_TERMINAL_ACTIVE),
    (BoundaryEvent.RESUME, SourceLifecycle.NON_TERMINAL_SUSPENDED),
    (BoundaryEvent.TERMINALIZE, SourceLifecycle.NON_TERMINAL_ACTIVE),
    (BoundaryEvent.TERMINALIZE, SourceLifecycle.NON_TERMINAL_SUSPENDED),
}

_ALL_CELLS = list(itertools.product(BoundaryEvent, SourceLifecycle))

# Expected required-mutation summary per legal event.
_EXPECTED_MUTATION = {
    BoundaryEvent.NEW: dict(
        target_lifecycle=LIFECYCLE_ACTIVE,
        allocate_workflow_id=True,
        keeps_workflow_id=False,
        clears_owner_lock=False,
        restores_owner_lock=True,
        links_predecessor_successor=False,
        terminalizes_predecessor=False,
        writes_prior_state=False,
        clears_prior_state=False,
        sets_terminal=False,
    ),
    BoundaryEvent.SUPERSEDE: dict(
        target_lifecycle=LIFECYCLE_ACTIVE,
        allocate_workflow_id=True,
        keeps_workflow_id=False,
        clears_owner_lock=False,
        restores_owner_lock=True,
        links_predecessor_successor=True,
        terminalizes_predecessor=True,
        writes_prior_state=False,
        clears_prior_state=False,
        sets_terminal=False,
    ),
    BoundaryEvent.SUSPEND: dict(
        target_lifecycle=LIFECYCLE_SUSPENDED,
        allocate_workflow_id=False,
        keeps_workflow_id=True,
        clears_owner_lock=True,
        restores_owner_lock=False,
        links_predecessor_successor=False,
        terminalizes_predecessor=False,
        writes_prior_state=True,
        clears_prior_state=False,
        sets_terminal=False,
    ),
    BoundaryEvent.RESUME: dict(
        target_lifecycle=LIFECYCLE_ACTIVE,
        allocate_workflow_id=False,
        keeps_workflow_id=True,
        clears_owner_lock=False,
        restores_owner_lock=True,
        links_predecessor_successor=False,
        terminalizes_predecessor=False,
        writes_prior_state=False,
        clears_prior_state=True,
        sets_terminal=False,
    ),
    BoundaryEvent.TERMINALIZE: dict(
        target_lifecycle=LIFECYCLE_TERMINAL,
        allocate_workflow_id=False,
        keeps_workflow_id=True,
        clears_owner_lock=True,
        restores_owner_lock=False,
        links_predecessor_successor=False,
        terminalizes_predecessor=False,
        writes_prior_state=False,
        clears_prior_state=False,
        sets_terminal=True,
    ),
}


@pytest.mark.parametrize("event,source", _ALL_CELLS)
def test_every_matrix_cell_legal_or_illegal(
    event: BoundaryEvent, source: SourceLifecycle
) -> None:
    result = evaluate_legality(event, source)
    expected_legal = (event, source) in _LEGAL_CELLS
    assert result.legal is expected_legal
    assert result.event is event
    assert result.source is source
    assert is_legal(event, source) is expected_legal
    if expected_legal:
        assert isinstance(result.mutation, StateMutation)
        assert "§4.4" in result.reason
    else:
        assert result.mutation is None
        assert result.reason  # deterministic, non-empty denial reason


@pytest.mark.parametrize("event,source", sorted(_LEGAL_CELLS, key=lambda c: (c[0].value, c[1].value)))
def test_legal_cell_required_mutation(
    event: BoundaryEvent, source: SourceLifecycle
) -> None:
    result = evaluate_legality(event, source)
    assert result.mutation is not None
    expected = _EXPECTED_MUTATION[event]
    for field_name, value in expected.items():
        assert getattr(result.mutation, field_name) == value, field_name


def test_new_over_suspended_is_illegal_and_non_destructive() -> None:
    # §4.5 ST-000 disambiguation: a `new` over a suspended workflow must be
    # illegal so it cannot silently discard the suspended workflow.
    result = evaluate_legality(BoundaryEvent.NEW, SourceLifecycle.NON_TERMINAL_SUSPENDED)
    assert result.legal is False
    assert result.mutation is None
    assert "silently discard" in result.reason


def test_new_over_active_is_illegal() -> None:
    result = evaluate_legality(BoundaryEvent.NEW, SourceLifecycle.NON_TERMINAL_ACTIVE)
    assert result.legal is False
    assert "suspend or supersede" in result.reason


def test_resume_from_terminal_is_illegal() -> None:
    result = evaluate_legality(BoundaryEvent.RESUME, SourceLifecycle.TERMINAL)
    assert result.legal is False
    assert "immutable" in result.reason


def test_unknown_event_type_fallback() -> None:
    result = evaluate_legality("not-an-event", SourceLifecycle.NONE)
    assert result.legal is False
    assert result.event is None
    assert result.source is SourceLifecycle.NONE
    assert result.mutation is None
    assert "unknown boundary event" in result.reason


def test_unknown_source_type_fallback() -> None:
    result = evaluate_legality(BoundaryEvent.NEW, "not-a-source")
    assert result.legal is False
    assert result.event is BoundaryEvent.NEW
    assert result.source is None
    assert result.mutation is None
