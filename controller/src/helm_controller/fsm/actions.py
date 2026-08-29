"""FSM actions AC-001..AC-012 — immutable static data (spec015 Task 5.1).

Transcribed faithfully from the normative source
``artifacts/docs/orchestration-fsm-policy-and-test-matrix.md`` §2.4.
"""

from __future__ import annotations

from enum import Enum
from types import MappingProxyType


class Action(Enum):
    """Orchestration FSM action. Enum value is the canonical AC-### id."""

    ROUTE_REQUEST = "AC-001"
    DISPATCH_SUBAGENT = "AC-002"
    PROMPT_OPEN_QUESTION_OPTIONS = "AC-003"
    INVOKE_CLARIFIER = "AC-004"
    PROMPT_APPROVAL = "AC-005"
    EXECUTE_PHASE = "AC-006"
    RESPOND_PROCESS_AUDIT = "AC-007"
    ACK_STOP = "AC-008"
    BLOCK_OUTBOUND_SEND = "AC-009"
    RESUME_PRE_INTERRUPT_STATE = "AC-010"
    MARK_TERMINAL = "AC-011"
    DIRECT_DELIVERABLE_BY_ORCHESTRATOR = "AC-012"


class UnknownActionError(KeyError):
    """Raised when an AC-### id has no corresponding :class:`Action` member."""


_BY_ID = MappingProxyType({action.value: action for action in Action})


def action_by_id(action_id: str) -> Action:
    """Return the :class:`Action` whose value is ``action_id``.

    Raises :class:`UnknownActionError` when no member matches.
    """
    if action_id not in _BY_ID:
        raise UnknownActionError(action_id)
    return _BY_ID[action_id]
