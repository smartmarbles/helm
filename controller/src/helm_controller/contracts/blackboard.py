"""Typed contract dataclass for the Profile #4 blackboard row (POL-052).

Mirrors ``artifacts/contracts/blackboard-row.schema.v1.json``. ``owner_lock.active``
and ``audit.created_by`` are agent NAMES preserved for audit fidelity, not roles;
policy enforcement (INV-021, POL-053) resolves the role separately. Gate outcomes
(BG-001..BG-006) are modeled as a ``dict`` because the keys are not valid Python
identifiers. Validate an instance with
:func:`helm_controller.contracts.validator.validate` against
:data:`helm_controller.contracts.validator.Contract.BLACKBOARD`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

SCHEMA_VERSION = "1.0.0"
CONTRACT_NAME = "blackboard-row"


@dataclass(frozen=True)
class OwnerLock:
    active: str | None
    lock_token: str | None
    acquired_at: str | None
    expires_at: str | None
    is_stale: bool
    active_lock_count: int


@dataclass(frozen=True)
class Terminal:
    is_terminal: bool
    terminal_state: str | None
    terminalized_at: str | None
    terminal_reason: str | None


@dataclass(frozen=True)
class Audit:
    created_at: str
    created_by: str
    revision: int
    immutable_fields_hash: str
    audit_fields_mutated: bool


@dataclass(frozen=True)
class BlackboardRow:
    row_present: bool
    row_schema_valid: bool
    row_id: str
    session_id: str
    workflow_id: str
    predecessor_workflow_id: str | None
    successor_workflow_id: str | None
    item_id: str
    lifecycle_stage: str
    workflow_lifecycle: str
    fsm_state_ref: str
    prior_non_terminal_fsm_state: str | None
    owner_lock: OwnerLock
    gates: dict[str, str]
    required_gates_passed: bool
    terminal: Terminal
    audit: Audit
    mutation_attempt_keys: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BlackboardRow":
        payload = dict(data)
        payload["owner_lock"] = OwnerLock(**data["owner_lock"])
        payload["terminal"] = Terminal(**data["terminal"])
        payload["audit"] = Audit(**data["audit"])
        payload["gates"] = dict(data["gates"])
        return cls(**payload)
