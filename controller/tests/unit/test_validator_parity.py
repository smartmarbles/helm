"""Full validation-parity characterization tests for the contract validator.

These tests lock the COMPLETE keyword surface the four real schemas exercise —
not just the narrow ``required``/``type``/``enum``/``additionalProperties``
slice the legacy suite covered. They are authored to pass against the original
``jsonschema`` engine (baseline lock) and MUST remain green after the engine is
replaced by the stdlib-only implementation, proving byte-stable behavior.

Each keyword has an accept case and a reject case. The error contract
(``ContractValidationError`` with ``.contract`` / ``.messages`` and
aggregate-all-errors, non-fail-fast) is asserted explicitly. The
``format: "date-time"`` non-enforcement parity is pinned so a future engine
cannot silently tighten validation.
"""

from __future__ import annotations

import pytest

from helm_controller.contracts.validator import (
    Contract,
    ContractValidationError,
    validate,
)
from tests.unit.test_contracts import (
    _blackboard_dict,
    _envelope_dict,
    _snapshot_dict,
)


def _valid_decision() -> dict:
    return {"decision": "allow", "reason_id": "CHK-001", "reason": "ok"}


# --- accept: every conformant real instance round-trips clean -------------


@pytest.mark.parametrize(
    ("factory", "contract"),
    [
        (_snapshot_dict, Contract.SNAPSHOT),
        (_blackboard_dict, Contract.BLACKBOARD),
        (_envelope_dict, Contract.ENVELOPE),
        (_valid_decision, Contract.DECISION),
    ],
)
def test_accepts_conformant_instances(factory, contract) -> None:
    assert validate(factory(), contract) is None


# --- required -------------------------------------------------------------


def test_required_accept_present() -> None:
    assert validate(_valid_decision(), Contract.DECISION) is None


def test_required_reject_missing() -> None:
    instance = _valid_decision()
    del instance["reason"]
    with pytest.raises(ContractValidationError) as exc:
        validate(instance, Contract.DECISION)
    assert exc.value.contract is Contract.DECISION
    assert any("required" in m for m in exc.value.messages)


# --- type: single + union ["string", "null"] ------------------------------


def test_type_single_reject_wrong() -> None:
    instance = _valid_decision()
    instance["reason"] = 5
    with pytest.raises(ContractValidationError):
        validate(instance, Contract.DECISION)


def test_type_union_accept_string_and_null() -> None:
    instance = _envelope_dict()
    instance["transcript_path"] = "/tmp/x"
    assert validate(instance, Contract.ENVELOPE) is None
    instance["transcript_path"] = None
    assert validate(instance, Contract.ENVELOPE) is None


def test_type_union_reject_outside_union() -> None:
    instance = _envelope_dict()
    instance["transcript_path"] = 123
    with pytest.raises(ContractValidationError):
        validate(instance, Contract.ENVELOPE)


def test_type_integer_rejects_bool() -> None:
    instance = _snapshot_dict()
    instance["open_question_count"] = True
    with pytest.raises(ContractValidationError):
        validate(instance, Contract.SNAPSHOT)


def test_type_boolean_accepts_bool_rejects_int() -> None:
    instance = _snapshot_dict()
    assert validate(instance, Contract.SNAPSHOT) is None
    instance["approval_prompted"] = 1
    with pytest.raises(ContractValidationError):
        validate(instance, Contract.SNAPSHOT)


# --- enum -----------------------------------------------------------------


def test_enum_accept_member() -> None:
    instance = _valid_decision()
    instance["decision"] = "ask"
    assert validate(instance, Contract.DECISION) is None


def test_enum_reject_non_member() -> None:
    instance = {"decision": "block", "reason_id": "CHK-001", "reason": "x"}
    with pytest.raises(ContractValidationError):
        validate(instance, Contract.DECISION)


# --- additionalProperties: false ------------------------------------------


def test_additional_properties_reject_extra() -> None:
    instance = _valid_decision()
    instance["surprise"] = 1
    with pytest.raises(ContractValidationError):
        validate(instance, Contract.DECISION)


def test_additional_properties_reject_nested_extra() -> None:
    instance = _snapshot_dict()
    instance["tool_calls"]["unexpected"] = 1
    with pytest.raises(ContractValidationError):
        validate(instance, Contract.SNAPSHOT)


# --- const (decision-output allOf/if/const guard) -------------------------


def test_const_continue_allowed_only_with_deny() -> None:
    instance = {
        "decision": "deny",
        "reason_id": "INV-021",
        "reason": "blocked",
        "continue": False,
    }
    assert validate(instance, Contract.DECISION) is None


def test_const_continue_rejected_without_deny() -> None:
    instance = {
        "decision": "allow",
        "reason_id": "CHK-001",
        "reason": "ok",
        "continue": False,
    }
    with pytest.raises(ContractValidationError):
        validate(instance, Contract.DECISION)


def test_const_continue_rejected_with_ask() -> None:
    instance = {
        "decision": "ask",
        "reason_id": "CHK-001",
        "reason": "ok",
        "continue": True,
    }
    with pytest.raises(ContractValidationError):
        validate(instance, Contract.DECISION)


# --- pattern (ID shapes) --------------------------------------------------


def test_pattern_accept_valid_id() -> None:
    instance = _valid_decision()
    instance["reason_id"] = "POL-014"
    assert validate(instance, Contract.DECISION) is None


def test_pattern_reject_malformed_id() -> None:
    instance = _valid_decision()
    instance["reason_id"] = "bogus"
    with pytest.raises(ContractValidationError):
        validate(instance, Contract.DECISION)


# --- local $ref into $defs ------------------------------------------------


def test_ref_accept_valid_state_id() -> None:
    instance = _snapshot_dict()
    instance["state_before"] = "ST-042"
    assert validate(instance, Contract.SNAPSHOT) is None


def test_ref_reject_invalid_state_id() -> None:
    instance = _snapshot_dict()
    instance["state_before"] = "ST-9"
    with pytest.raises(ContractValidationError):
        validate(instance, Contract.SNAPSHOT)


# --- oneOf (exactly one, including the null branch) -----------------------


def test_one_of_accept_ref_branch() -> None:
    instance = _snapshot_dict()
    instance["prior_non_terminal_fsm_state"] = "ST-007"
    assert validate(instance, Contract.SNAPSHOT) is None


def test_one_of_accept_null_branch() -> None:
    instance = _snapshot_dict()
    instance["prior_non_terminal_fsm_state"] = None
    assert validate(instance, Contract.SNAPSHOT) is None


def test_one_of_reject_no_branch() -> None:
    instance = _snapshot_dict()
    instance["prior_non_terminal_fsm_state"] = "not-a-state"
    with pytest.raises(ContractValidationError):
        validate(instance, Contract.SNAPSHOT)


# --- propertyNames pattern on blackboard.gates ----------------------------


def test_property_names_accept_valid_keys() -> None:
    assert validate(_blackboard_dict(), Contract.BLACKBOARD) is None


def test_property_names_reject_bad_key() -> None:
    instance = _blackboard_dict()
    instance["gates"]["nope"] = "pass"
    with pytest.raises(ContractValidationError):
        validate(instance, Contract.BLACKBOARD)


# --- minLength ------------------------------------------------------------


def test_min_length_accept_nonempty() -> None:
    assert validate(_snapshot_dict(), Contract.SNAPSHOT) is None


def test_min_length_reject_empty_string() -> None:
    instance = _snapshot_dict()
    instance["session_id"] = ""
    with pytest.raises(ContractValidationError):
        validate(instance, Contract.SNAPSHOT)


# --- minimum --------------------------------------------------------------


def test_minimum_accept_zero() -> None:
    instance = _snapshot_dict()
    instance["open_question_count"] = 0
    assert validate(instance, Contract.SNAPSHOT) is None


def test_minimum_reject_negative() -> None:
    instance = _snapshot_dict()
    instance["open_question_count"] = -1
    with pytest.raises(ContractValidationError):
        validate(instance, Contract.SNAPSHOT)


# --- format: "date-time" is NON-enforcing (annotation only) ---------------


def test_format_date_time_is_not_enforced() -> None:
    instance = _blackboard_dict()
    instance["audit"]["created_at"] = "definitely not a timestamp"
    # Must be ACCEPTED — today's behavior wires no format_checker.
    assert validate(instance, Contract.BLACKBOARD) is None


# --- error contract: aggregate-all-errors (non-fail-fast) -----------------


def test_aggregate_all_errors_collects_multiple() -> None:
    instance = _valid_decision()
    del instance["reason"]
    del instance["reason_id"]
    with pytest.raises(ContractValidationError) as exc:
        validate(instance, Contract.DECISION)
    assert exc.value.contract is Contract.DECISION
    assert len(exc.value.messages) >= 2


def test_error_str_includes_contract_and_messages() -> None:
    instance = _valid_decision()
    del instance["decision"]
    with pytest.raises(ContractValidationError) as exc:
        validate(instance, Contract.DECISION)
    text = str(exc.value)
    assert "decision-output validation failed" in text
    assert exc.value.messages
