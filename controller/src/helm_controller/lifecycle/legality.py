"""Boundary-event legality matrix and required state mutations (Task 7.1).

Transcribed faithfully from spec §4.4 ("Lifecycle Transition Table (Control
Intent)") and the §4.3 normative lifecycle rules. The matrix is the single
source of truth for whether a ``(source-lifecycle, boundary-event)`` pair is
legal and, when legal, which runtime-store mutations the evaluator MUST apply
(``workflow_id`` allocation, predecessor/successor linkage, owner-lock
clear/restore, ``prior_non_terminal_fsm_state`` write/clear).

``workflow_id`` allocation is NOT performed here — :data:`StateMutation`
declares *that* a new id is required; the evaluator (Task 7.2) imports
``new_workflow_id`` from :mod:`helm_controller.store.identity` (the sole
``str(uuid.uuid4())`` path, spec015 Task 2.4) to produce it. This module never
generates ids.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

# Lifecycle class string values mirror the runtime store's ``workflow_lifecycle``
# column (spec §4.1); ``NONE`` models "no active workflow" (spec §4.4 source
# column "Any terminal or no active workflow").
LIFECYCLE_ACTIVE = "non_terminal_active"
LIFECYCLE_SUSPENDED = "non_terminal_suspended"
LIFECYCLE_TERMINAL = "terminal"


class SourceLifecycle(Enum):
    """The source lifecycle class a boundary event is evaluated against (§4.1)."""

    NONE = "none"
    NON_TERMINAL_ACTIVE = LIFECYCLE_ACTIVE
    NON_TERMINAL_SUSPENDED = LIFECYCLE_SUSPENDED
    TERMINAL = LIFECYCLE_TERMINAL


class BoundaryEvent(Enum):
    """The five explicit session/workflow boundary events (spec §4.2)."""

    NEW = "new"
    SUPERSEDE = "supersede"
    SUSPEND = "suspend"
    RESUME = "resume"
    TERMINALIZE = "terminalize"


@dataclass(frozen=True)
class StateMutation:
    """The runtime-store mutations a legal boundary event requires (§4.4).

    Declarative only — describes *what* must change. The evaluator (Task 7.2)
    reads these flags to drive the concrete store write path; this module never
    touches the store.
    """

    target_lifecycle: str
    allocate_workflow_id: bool
    keeps_workflow_id: bool
    clears_owner_lock: bool
    restores_owner_lock: bool
    links_predecessor_successor: bool
    terminalizes_predecessor: bool
    writes_prior_state: bool
    clears_prior_state: bool
    sets_terminal: bool


@dataclass(frozen=True)
class LegalityResult:
    """Outcome of a single matrix-cell evaluation."""

    legal: bool
    event: BoundaryEvent | None
    source: SourceLifecycle | None
    reason: str
    mutation: StateMutation | None


# --------------------------------------------------------------------------- #
# Required-mutation builders (one per legal event), per §4.4 / §4.3.
# --------------------------------------------------------------------------- #
def _new_mutation() -> StateMutation:
    # §4.4 `new`: allocate new id, start a clean active process; the new
    # workflow takes an active owner lock. No predecessor linkage.
    return StateMutation(
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
    )


def _supersede_mutation() -> StateMutation:
    # §4.4 `supersede`: allocate successor id; predecessor terminalized and
    # linked to the successor; successor takes the active owner lock.
    return StateMutation(
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
    )


def _suspend_mutation() -> StateMutation:
    # §4.4 `suspend`: keep id; preserve the workflow row but clear active
    # ownership; write `prior_non_terminal_fsm_state` (POL-014C, TR-033).
    return StateMutation(
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
    )


def _resume_mutation() -> StateMutation:
    # §4.4 `resume`: keep id; reactivate the same row and regain the active
    # owner lock; clear `prior_non_terminal_fsm_state` (POL-014C, TR-034).
    return StateMutation(
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
    )


def _terminalize_mutation() -> StateMutation:
    # §4.4 `terminalize`: keep id; freeze the row permanently; no active owner
    # lease on a terminal workflow (spec §5.3 Rule 2).
    return StateMutation(
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
    )


# --------------------------------------------------------------------------- #
# Legal cells of the §4.4 matrix. Every (event, source) pair NOT listed here is
# illegal and fails closed (spec §4.5 scenario 5).
# --------------------------------------------------------------------------- #
_LEGAL_CELLS: dict[tuple[BoundaryEvent, SourceLifecycle], StateMutation] = {
    # `new`: "Any terminal or no active workflow" (§4.4). NOT legal over a
    # non-terminal active OR suspended workflow — a `new` over a suspended
    # workflow would silently discard it (spec §4.5 ST-000 disambiguation).
    (BoundaryEvent.NEW, SourceLifecycle.NONE): _new_mutation(),
    (BoundaryEvent.NEW, SourceLifecycle.TERMINAL): _new_mutation(),
    # `supersede`: from a non-terminal active OR suspended workflow (§4.4).
    (BoundaryEvent.SUPERSEDE, SourceLifecycle.NON_TERMINAL_ACTIVE): _supersede_mutation(),
    (BoundaryEvent.SUPERSEDE, SourceLifecycle.NON_TERMINAL_SUSPENDED): _supersede_mutation(),
    # `suspend`: only from a non-terminal active workflow (§4.4).
    (BoundaryEvent.SUSPEND, SourceLifecycle.NON_TERMINAL_ACTIVE): _suspend_mutation(),
    # `resume`: only from a non-terminal suspended workflow (§4.3 Rule 2, §4.4).
    (BoundaryEvent.RESUME, SourceLifecycle.NON_TERMINAL_SUSPENDED): _resume_mutation(),
    # `terminalize`: from any non-terminal workflow (§4.4).
    (BoundaryEvent.TERMINALIZE, SourceLifecycle.NON_TERMINAL_ACTIVE): _terminalize_mutation(),
    (BoundaryEvent.TERMINALIZE, SourceLifecycle.NON_TERMINAL_SUSPENDED): _terminalize_mutation(),
}

_LEGAL_INDEX = MappingProxyType(dict(_LEGAL_CELLS))

# Deterministic per-cell denial reasons (spec §4.5 scenario 5 fail-closed).
_ILLEGAL_REASONS: dict[tuple[BoundaryEvent, SourceLifecycle], str] = {
    (BoundaryEvent.NEW, SourceLifecycle.NON_TERMINAL_ACTIVE): (
        "`new` is illegal over a non-terminal active workflow; suspend or "
        "supersede the active workflow first (§4.3 Rule 5)"
    ),
    (BoundaryEvent.NEW, SourceLifecycle.NON_TERMINAL_SUSPENDED): (
        "`new` is illegal over a non-terminal suspended workflow; it would "
        "silently discard the suspended workflow (§4.5 ST-000 disambiguation) — "
        "use `resume` or `supersede`"
    ),
    (BoundaryEvent.SUPERSEDE, SourceLifecycle.NONE): (
        "`supersede` requires a non-terminal predecessor (§4.4)"
    ),
    (BoundaryEvent.SUPERSEDE, SourceLifecycle.TERMINAL): (
        "`supersede` is illegal from a terminal workflow; a terminal workflow "
        "has no live process to replace (§4.3 Rule 1)"
    ),
    (BoundaryEvent.SUSPEND, SourceLifecycle.NONE): (
        "`suspend` requires a non-terminal active workflow (§4.4)"
    ),
    (BoundaryEvent.SUSPEND, SourceLifecycle.NON_TERMINAL_SUSPENDED): (
        "`suspend` is illegal on an already-suspended workflow (§4.4)"
    ),
    (BoundaryEvent.SUSPEND, SourceLifecycle.TERMINAL): (
        "`suspend` is illegal on a terminal workflow (§4.3 Rule 1)"
    ),
    (BoundaryEvent.RESUME, SourceLifecycle.NONE): (
        "`resume` is illegal when no workflow is suspended (§4.5 scenario 5)"
    ),
    (BoundaryEvent.RESUME, SourceLifecycle.NON_TERMINAL_ACTIVE): (
        "`resume` is illegal on an already-active workflow (§4.3 Rule 2)"
    ),
    (BoundaryEvent.RESUME, SourceLifecycle.TERMINAL): (
        "`resume` is illegal from a terminal workflow; terminal workflows are "
        "immutable and MUST NOT be resumed (§4.3 Rule 1)"
    ),
    (BoundaryEvent.TERMINALIZE, SourceLifecycle.NONE): (
        "`terminalize` requires a non-terminal workflow (§4.4)"
    ),
    (BoundaryEvent.TERMINALIZE, SourceLifecycle.TERMINAL): (
        "`terminalize` is illegal on an already-terminal workflow (§4.3 Rule 6)"
    ),
}


def evaluate_legality(event: Any, source: Any) -> LegalityResult:
    """Evaluate one ``(boundary-event, source-lifecycle)`` cell of the §4.4 matrix.

    Returns a legal result with the required :class:`StateMutation` for a legal
    cell, or an illegal result (``mutation is None``) with a deterministic
    fail-closed reason. An ``event`` or ``source`` outside the known enums hits
    the unknown-event fallback — this branch is NOT reachable through the
    evaluator's own control flow (it only ever passes valid enum members) and is
    exercised directly in ``test_legality.py``.
    """
    if not isinstance(event, BoundaryEvent) or not isinstance(source, SourceLifecycle):
        return LegalityResult(
            legal=False,
            event=event if isinstance(event, BoundaryEvent) else None,
            source=source if isinstance(source, SourceLifecycle) else None,
            reason=f"unknown boundary event/source: event={event!r} source={source!r}",
            mutation=None,
        )
    mutation = _LEGAL_INDEX.get((event, source))
    if mutation is not None:
        return LegalityResult(
            legal=True,
            event=event,
            source=source,
            reason=f"{event.value} is legal from {source.value} (§4.4)",
            mutation=mutation,
        )
    return LegalityResult(
        legal=False,
        event=event,
        source=source,
        reason=_ILLEGAL_REASONS[(event, source)],
        mutation=None,
    )


def is_legal(event: BoundaryEvent, source: SourceLifecycle) -> bool:
    """Convenience predicate: ``True`` iff ``(event, source)`` is a legal cell."""
    return (event, source) in _LEGAL_INDEX
