"""Single JSON Schema validation entry point for all four Helm contracts.

The authored schemas live in the repository's ``artifacts/contracts/``
directory (the external validation contract). This module locates that
directory, loads the versioned schemas, and exposes one :func:`validate`
function used across the snapshot, blackboard, envelope, and decision
contracts. Compiled validators are cached per contract.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

from helm_controller.contracts import _jsonschema_lite

CONTRACTS_DIR_ENV = "HELM_CONTRACTS_DIR"


class Contract(str, Enum):
    """The four versioned contract identities, keyed by schema file stem."""

    SNAPSHOT = "runtime-snapshot"
    BLACKBOARD = "blackboard-row"
    ENVELOPE = "hook-envelope"
    DECISION = "decision-output"


class ContractValidationError(Exception):
    """Raised when an instance fails validation against its contract schema."""

    def __init__(self, contract: Contract, messages: list[str]) -> None:
        self.contract = contract
        self.messages = messages
        joined = "; ".join(messages)
        super().__init__(f"{contract.value} validation failed: {joined}")


def validate(instance: Mapping[str, Any], contract: Contract) -> None:
    """Validate ``instance`` against ``contract``'s JSON Schema.

    Raises :class:`ContractValidationError` aggregating every schema
    violation when the instance does not conform; returns ``None`` on success.
    """
    validator = _validator_for(contract)
    errors = sorted(validator.collect(instance), key=lambda err: [str(p) for p in err[0]])
    if errors:
        raise ContractValidationError(contract, [message for _, message in errors])


def schema_version(contract: Contract) -> str:
    """Return the top-level ``version`` property of ``contract``'s schema."""
    return str(_load_schema(contract)["version"])


def _contracts_dir() -> Path:
    override = os.environ.get(CONTRACTS_DIR_ENV)
    if override:
        path = Path(override)
        if not path.is_dir():
            raise ContractValidationError(
                Contract.SNAPSHOT,
                [f"{CONTRACTS_DIR_ENV} is not a directory: {path}"],
            )
        return path
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "artifacts" / "contracts"
        if candidate.is_dir():
            return candidate
    raise ContractValidationError(
        Contract.SNAPSHOT,
        ["could not locate the artifacts/contracts directory"],
    )


@lru_cache(maxsize=None)
def _load_schema(contract: Contract) -> dict[str, Any]:
    path = _contracts_dir() / f"{contract.value}.schema.v1.json"
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=None)
def _validator_for(contract: Contract) -> _jsonschema_lite.SchemaValidator:
    return _jsonschema_lite.compile_schema(_load_schema(contract))
