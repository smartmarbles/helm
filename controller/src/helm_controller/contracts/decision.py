"""Typed contract dataclass for the Python decision output (boundary contract §4.3).

Mirrors ``artifacts/contracts/decision-output.schema.v1.json``. The decision
vocabulary is exactly ``allow|deny|ask`` — the token ``block`` is never a valid
value. ``continue`` is a reserved Python keyword, so it is modeled as the field
``continue_`` and mapped to/from the JSON key ``continue``; it is permitted only
alongside ``decision == "deny"``. Validate an instance with
:func:`helm_controller.contracts.validator.validate` against
:data:`helm_controller.contracts.validator.Contract.DECISION`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SCHEMA_VERSION = "1.0.0"
CONTRACT_NAME = "decision-output"


@dataclass(frozen=True)
class Decision:
    decision: str
    reason_id: str
    reason: str
    state_after: str | None = None
    suppressed_action_ids: list[str] | None = None
    additional_context: str | None = None
    updated_input: dict[str, Any] | None = None
    continue_: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "decision": self.decision,
            "reason_id": self.reason_id,
            "reason": self.reason,
        }
        if self.state_after is not None:
            out["state_after"] = self.state_after
        if self.suppressed_action_ids is not None:
            out["suppressed_action_ids"] = list(self.suppressed_action_ids)
        if self.additional_context is not None:
            out["additional_context"] = self.additional_context
        if self.updated_input is not None:
            out["updated_input"] = self.updated_input
        if self.continue_ is not None:
            out["continue"] = self.continue_
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Decision":
        return cls(
            decision=data["decision"],
            reason_id=data["reason_id"],
            reason=data["reason"],
            state_after=data.get("state_after"),
            suppressed_action_ids=data.get("suppressed_action_ids"),
            additional_context=data.get("additional_context"),
            updated_input=data.get("updated_input"),
            continue_=data.get("continue"),
        )
