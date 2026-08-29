"""FSM events EV-001..EV-025 — immutable static data (spec015 Task 5.1).

Transcribed faithfully from the normative source
``artifacts/docs/orchestration-fsm-policy-and-test-matrix.md`` §2.2.
"""

from __future__ import annotations

from enum import Enum
from types import MappingProxyType


class Event(Enum):
    """Orchestration FSM event. Enum value is the canonical EV-### id."""

    USER_WORK_REQUEST = "EV-001"
    USER_STOP = "EV-002"
    USER_PROCESS_AUDIT_OR_META = "EV-003"
    PATH_SELECTED = "EV-004"
    DISPATCH_SENT = "EV-005"
    SUBAGENT_RESULT_SPEC = "EV-006"
    SUBAGENT_RESULT_PLAN = "EV-007"
    SUBAGENT_RESULT_NON_GATE_DOC = "EV-008"
    OPEN_QUESTIONS_PRESENT = "EV-009"
    OPEN_QUESTIONS_ABSENT = "EV-010"
    USER_CHOICE_QUIZ = "EV-011"
    USER_CHOICE_INLINE = "EV-012"
    USER_CHOICE_DEFER = "EV-013"
    QUIZ_HANDOFF_COMPLETE = "EV-014"
    USER_APPROVE = "EV-015"
    USER_REVISE = "EV-016"
    USER_REJECT = "EV-017"
    PHASE_DONE_MORE = "EV-018"
    PHASE_DONE_ALL = "EV-019"
    PRE_SEND_FAIL = "EV-020"
    PRE_SEND_PASS = "EV-021"
    AUDIT_RESPONSE_SENT = "EV-022"
    WORKFLOW_COMPLETE = "EV-023"
    USER_SUSPEND_WORKFLOW = "EV-024"
    USER_RESUME_WORKFLOW = "EV-025"


class UnknownEventError(KeyError):
    """Raised when an EV-### id has no corresponding :class:`Event` member."""


_BY_ID = MappingProxyType({event.value: event for event in Event})


def event_by_id(event_id: str) -> Event:
    """Return the :class:`Event` whose value is ``event_id``.

    Raises :class:`UnknownEventError` when no member matches.
    """
    if event_id not in _BY_ID:
        raise UnknownEventError(event_id)
    return _BY_ID[event_id]
