"""FSM guards GD-001..GD-015 — immutable predicates over the runtime snapshot
(spec015 Task 5.1).

Each guard is a pure callable ``(Snapshot) -> bool`` transcribed faithfully from
the normative source
``artifacts/docs/orchestration-fsm-policy-and-test-matrix.md`` §2.3. Guards read
only the per-turn snapshot context; they never mutate state.

EV-009 (OPEN_QUESTIONS_PRESENT) and EV-010 (OPEN_QUESTIONS_ABSENT) are by
definition the same conditions as GD-005 (``open_question_count > 0``) and GD-006
(``open_question_count == 0``); the transition table (§2.5) encodes those
co-events through these guards.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from types import MappingProxyType

from helm_controller.contracts.snapshot import Snapshot
from helm_controller.fsm.states import TERMINAL_STATE_IDS


class Guard(Enum):
    """Orchestration FSM guard. Enum value is the canonical GD-### id."""

    GD_001 = "GD-001"
    GD_002 = "GD-002"
    GD_003 = "GD-003"
    GD_004 = "GD-004"
    GD_005 = "GD-005"
    GD_006 = "GD-006"
    GD_007 = "GD-007"
    GD_008 = "GD-008"
    GD_009 = "GD-009"
    GD_010 = "GD-010"
    GD_011 = "GD-011"
    GD_012 = "GD-012"
    GD_013 = "GD-013"
    GD_014 = "GD-014"
    GD_015 = "GD-015"


class UnknownGuardError(KeyError):
    """Raised when a GD-### id has no corresponding :class:`Guard` member."""


def _gd_001(snapshot: Snapshot) -> bool:
    return snapshot.explicit_path is not None


def _gd_002(snapshot: Snapshot) -> bool:
    return snapshot.doc_type == "spec"


def _gd_003(snapshot: Snapshot) -> bool:
    return snapshot.doc_type == "plan"


def _gd_004(snapshot: Snapshot) -> bool:
    return snapshot.doc_type == "non_gate"


def _gd_005(snapshot: Snapshot) -> bool:
    return snapshot.open_question_count > 0


def _gd_006(snapshot: Snapshot) -> bool:
    return snapshot.open_question_count == 0


def _gd_007(snapshot: Snapshot) -> bool:
    return snapshot.owner_before == "orchestrator"


def _gd_008(snapshot: Snapshot) -> bool:
    return snapshot.owner_before == "clarifier"


def _gd_009(snapshot: Snapshot) -> bool:
    return snapshot.state_before not in TERMINAL_STATE_IDS


def _gd_010(snapshot: Snapshot) -> bool:
    return snapshot.presend.result == "pass"


def _gd_011(snapshot: Snapshot) -> bool:
    return snapshot.workflow_lifecycle_before == "non_terminal_active"


def _gd_012(snapshot: Snapshot) -> bool:
    return snapshot.workflow_lifecycle_before == "non_terminal_suspended"


def _gd_013(snapshot: Snapshot) -> bool:
    return snapshot.session_active_workflow_id == snapshot.workflow_id


def _gd_014(snapshot: Snapshot) -> bool:
    return snapshot.session_active_workflow_id is None


def _gd_015(snapshot: Snapshot) -> bool:
    return snapshot.boundary_event == "supersede"


GUARD_FUNCS: "MappingProxyType[Guard, Callable[[Snapshot], bool]]" = MappingProxyType(
    {
        Guard.GD_001: _gd_001,
        Guard.GD_002: _gd_002,
        Guard.GD_003: _gd_003,
        Guard.GD_004: _gd_004,
        Guard.GD_005: _gd_005,
        Guard.GD_006: _gd_006,
        Guard.GD_007: _gd_007,
        Guard.GD_008: _gd_008,
        Guard.GD_009: _gd_009,
        Guard.GD_010: _gd_010,
        Guard.GD_011: _gd_011,
        Guard.GD_012: _gd_012,
        Guard.GD_013: _gd_013,
        Guard.GD_014: _gd_014,
        Guard.GD_015: _gd_015,
    }
)

_BY_ID = MappingProxyType({guard.value: guard for guard in Guard})


def guard_by_id(guard_id: str) -> Guard:
    """Return the :class:`Guard` whose value is ``guard_id``.

    Raises :class:`UnknownGuardError` when no member matches.
    """
    if guard_id not in _BY_ID:
        raise UnknownGuardError(guard_id)
    return _BY_ID[guard_id]


def evaluate_guard(guard: Guard, snapshot: Snapshot) -> bool:
    """Evaluate ``guard`` against ``snapshot`` and return its boolean result."""
    return GUARD_FUNCS[guard](snapshot)
