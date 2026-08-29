"""Typed contract objects and the single JSON Schema validation entry point.

Re-exports the four contract dataclasses (snapshot, blackboard, envelope,
decision) and the shared :func:`validate` function so callers import from one
place::

    from helm_controller.contracts import Snapshot, Contract, validate
    validate(snap.to_dict(), Contract.SNAPSHOT)
"""

from __future__ import annotations

from helm_controller.contracts.blackboard import (
    Audit,
    BlackboardRow,
    OwnerLock,
    Terminal,
)
from helm_controller.contracts.decision import Decision
from helm_controller.contracts.envelope import (
    Actor,
    BlackboardContext,
    Envelope,
    ToolAttempt,
    WorkflowContext,
)
from helm_controller.contracts.snapshot import Presend, Snapshot, ToolCalls
from helm_controller.contracts.validator import (
    Contract,
    ContractValidationError,
    schema_version,
    validate,
)

__all__ = [
    "Actor",
    "Audit",
    "BlackboardContext",
    "BlackboardRow",
    "Contract",
    "ContractValidationError",
    "Decision",
    "Envelope",
    "OwnerLock",
    "Presend",
    "Snapshot",
    "Terminal",
    "ToolAttempt",
    "ToolCalls",
    "WorkflowContext",
    "schema_version",
    "validate",
]
