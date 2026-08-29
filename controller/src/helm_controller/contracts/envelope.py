"""Typed contract dataclass for the normalized hook envelope (boundary contract §4.2).

Mirrors ``artifacts/contracts/hook-envelope.schema.v1.json`` — the input passed
to the Python policy controller for every hook event. Validate an instance with
:func:`helm_controller.contracts.validator.validate` against
:data:`helm_controller.contracts.validator.Contract.ENVELOPE`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

SCHEMA_VERSION = "1.0.0"
CONTRACT_NAME = "hook-envelope"


@dataclass(frozen=True)
class Actor:
    active_agent: str
    active_role: str
    subagent_id: str | None


@dataclass(frozen=True)
class ToolAttempt:
    tool_name: str | None
    tool_use_id: str | None
    tool_input: dict[str, Any] | None
    tool_response: dict[str, Any] | None


@dataclass(frozen=True)
class WorkflowContext:
    workflow_id: str | None
    turn_id: str | None
    state_before: str | None
    selected_path: str | None
    explicit_path: str | None
    doc_type: str | None
    open_question_count: int | None
    user_choice: str | None
    approval_prompted: bool | None


@dataclass(frozen=True)
class BlackboardContext:
    row_present: bool | None
    row_schema_valid: bool | None
    row_id: str | None
    lifecycle_stage: str | None
    fsm_state_ref: str | None
    required_gates_passed: bool | None
    gates: dict[str, str | None]


@dataclass(frozen=True)
class Envelope:
    policy_version: str
    hook_event: str
    timestamp: str
    session_id: str
    workspace_root: str
    transcript_path: str | None
    actor: Actor
    tool_attempt: ToolAttempt
    workflow: WorkflowContext
    blackboard: BlackboardContext

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Envelope":
        payload = dict(data)
        payload["actor"] = Actor(**data["actor"])
        payload["tool_attempt"] = ToolAttempt(**data["tool_attempt"])
        payload["workflow"] = WorkflowContext(**data["workflow"])
        payload["blackboard"] = BlackboardContext(**data["blackboard"])
        return cls(**payload)
