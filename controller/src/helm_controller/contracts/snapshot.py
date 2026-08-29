"""Typed contract dataclass for the per-turn runtime snapshot (POL-009 + GAP-011).

Mirrors ``artifacts/contracts/runtime-snapshot.schema.v1.json``. Storage-tier
annotations are schema metadata, not encoded here; this module models the data
shape and provides round-trip ``to_dict`` / ``from_dict`` helpers. Validate an
instance with :func:`helm_controller.contracts.validator.validate` against
:data:`helm_controller.contracts.validator.Contract.SNAPSHOT`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

SCHEMA_VERSION = "1.0.0"
CONTRACT_NAME = "runtime-snapshot"


@dataclass(frozen=True)
class ToolCalls:
    runSubagent: int


@dataclass(frozen=True)
class Presend:
    executed: bool
    result: str
    failed_check: str | None


@dataclass(frozen=True)
class Snapshot:
    session_id: str
    workflow_id: str
    session_active_workflow_id: str | None
    predecessor_workflow_id: str | None
    successor_workflow_id: str | None
    workflow_lifecycle_before: str
    workflow_lifecycle_after: str
    turn_id: str
    state_before: str
    state_after: str
    prior_non_terminal_fsm_state: str | None
    owner_before: str
    owner_after: str
    event: str
    boundary_event: str | None
    selected_path: str | None
    explicit_path: str | None
    doc_type: str | None
    open_question_count: int
    pending_interrupt: str
    actions: list[str]
    outbound_sender: str
    outbound_message_type: str
    prompt_options: list[str]
    user_choice: str | None
    approval_prompted: bool
    open_question_protocol_resolved: bool
    delegation_claimed: bool
    dispatch_payload_keys: list[str]
    phase_execution_started: bool
    suppressed_action_ids: list[str]
    tool_calls: ToolCalls
    presend: Presend
    output_paths: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Snapshot":
        payload = dict(data)
        payload["tool_calls"] = ToolCalls(**data["tool_calls"])
        payload["presend"] = Presend(**data["presend"])
        return cls(**payload)
