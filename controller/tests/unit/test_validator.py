"""Tests for the single JSON Schema validation entry point."""

from __future__ import annotations

import pytest

from helm_controller.contracts import (
    blackboard,
    decision,
    envelope,
    snapshot,
    validator,
)
from helm_controller.contracts.validator import (
    Contract,
    ContractValidationError,
    schema_version,
    validate,
)
from tests.unit.test_contracts import (
    _blackboard_dict,
    _envelope_dict,
    _snapshot_dict,
)


def _valid_decision() -> dict:
    return {"decision": "allow", "reason_id": "CHK-001", "reason": "ok"}


@pytest.mark.parametrize(
    ("instance_factory", "contract"),
    [
        (_snapshot_dict, Contract.SNAPSHOT),
        (_blackboard_dict, Contract.BLACKBOARD),
        (_envelope_dict, Contract.ENVELOPE),
        (_valid_decision, Contract.DECISION),
    ],
)
def test_validate_accepts_conformant_instance(instance_factory, contract) -> None:
    assert validate(instance_factory(), contract) is None


def test_validate_rejects_missing_required_field() -> None:
    instance = _valid_decision()
    del instance["decision"]
    with pytest.raises(ContractValidationError) as excinfo:
        validate(instance, Contract.DECISION)
    assert excinfo.value.contract is Contract.DECISION
    assert excinfo.value.messages


def test_validate_rejects_wrong_type_field() -> None:
    instance = _valid_decision()
    instance["reason_id"] = 5
    with pytest.raises(ContractValidationError):
        validate(instance, Contract.DECISION)


def test_validate_rejects_unknown_extra_field() -> None:
    instance = _valid_decision()
    instance["unexpected"] = True
    with pytest.raises(ContractValidationError):
        validate(instance, Contract.DECISION)


def test_block_is_not_a_valid_decision_value() -> None:
    instance = {"decision": "block", "reason_id": "CHK-001", "reason": "x"}
    with pytest.raises(ContractValidationError):
        validate(instance, Contract.DECISION)


@pytest.mark.parametrize(
    ("contract", "module"),
    [
        (Contract.SNAPSHOT, snapshot),
        (Contract.BLACKBOARD, blackboard),
        (Contract.ENVELOPE, envelope),
        (Contract.DECISION, decision),
    ],
)
def test_schema_version_matches_module_constant(contract, module) -> None:
    assert schema_version(contract) == module.SCHEMA_VERSION


def test_contracts_dir_env_override_to_valid_dir(monkeypatch) -> None:
    real_dir = validator._contracts_dir()
    monkeypatch.setenv(validator.CONTRACTS_DIR_ENV, str(real_dir))
    assert validator._contracts_dir() == real_dir


def test_contracts_dir_env_override_to_missing_dir(monkeypatch, tmp_path) -> None:
    missing = tmp_path / "does-not-exist"
    monkeypatch.setenv(validator.CONTRACTS_DIR_ENV, str(missing))
    with pytest.raises(ContractValidationError):
        validator._contracts_dir()


def test_contracts_dir_not_found_when_no_ancestor(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv(validator.CONTRACTS_DIR_ENV, raising=False)
    monkeypatch.setattr(validator, "__file__", str(tmp_path / "validator.py"))
    with pytest.raises(ContractValidationError):
        validator._contracts_dir()
