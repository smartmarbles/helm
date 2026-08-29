"""Composite runtime identity for runtime-store records (spec015 Task 2.2).

Every runtime-store record is addressed by the triple
``(session_id, workflow_id, turn_id)``. ``session_id`` and ``workflow_id``
locate the workflow-scoped persistent record in the store (the
``(session_id, workflow_id)`` primary key on ``workflows``); ``turn_id``
correlates the addressing user-prompt turn (spec §5.1 storage tiers).

The triple is modeled as a frozen, hashable dataclass so it can be used as a
dict key and compared for equality. Field validation rejects ``None`` and
empty values explicitly so the caller fails fast at the boundary rather than
emitting a malformed identity into the store layer.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

_REQUIRED_FIELDS = ("session_id", "workflow_id", "turn_id")


def new_workflow_id() -> str:
    """Generate a fresh ``workflow_id``.

    This is the ONLY ``workflow_id`` generation path in the codebase (spec015
    Task 2.4): ``str(uuid.uuid4())``. UUIDs prevent collision across concurrent
    sessions and survive process restart without coordination. Boundary-event
    allocation (Task 7.1) imports this function rather than re-implementing it;
    a grep assertion in ``test_identity.py`` enforces single-source.
    """
    return str(uuid.uuid4())


class IdentityError(ValueError):
    """Raised when a composite runtime identity is malformed."""


@dataclass(frozen=True)
class RuntimeIdentity:
    """The ``(session_id, workflow_id, turn_id)`` composite store identity."""

    session_id: str
    workflow_id: str
    turn_id: str

    def __post_init__(self) -> None:
        for name in _REQUIRED_FIELDS:
            value = getattr(self, name)
            if value is None:
                raise IdentityError(f"{name} must not be None")
            if not isinstance(value, str):
                raise IdentityError(
                    f"{name} must be a str, got {type(value).__name__}"
                )
            if not value:
                raise IdentityError(f"{name} must not be empty")
