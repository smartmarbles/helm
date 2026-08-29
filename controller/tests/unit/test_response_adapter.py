"""Tests for the SECURITY-CRITICAL response adapter (spec015 Task 8.2 / 8.5).

Exhaustively exercises ``to_wire`` across the permission / block / common
families and the fail-closed path, and proves every emitted shape validates
against ``hook-wire-output.schema.v1.json`` via the stdlib ``_jsonschema_lite``
validator (NOT third-party jsonschema). The cardinal invariants under test:

* a ``PreToolUse`` verdict rides ``hookSpecificOutput.permissionDecision`` and
  NEVER emits a bare top-level ``decision`` key (failing open in VS Code);
* an unrecognized / empty / ``None`` internal decision resolves to DENY, never a
  silent pass-through (Watch Out #15).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from helm_controller.contracts._jsonschema_lite import compile_schema
from helm_controller.contracts.decision import Decision
from helm_controller.hooks.response_adapter import to_wire


def _wire_validator():
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = (
            parent / "artifacts" / "contracts" / "hook-wire-output.schema.v1.json"
        )
        if candidate.is_file():
            return compile_schema(json.loads(candidate.read_text(encoding="utf-8")))
    raise RuntimeError("hook-wire-output.schema.v1.json not found")


_VALIDATOR = _wire_validator()


def _assert_valid(wire: dict) -> None:
    errors = [message for _, message in _VALIDATOR.collect(wire)]
    assert errors == [], errors


def _decision(
    verdict: str = "allow",
    *,
    reason_id: str = "PC-000",
    reason: str = "reason text",
    additional_context: str | None = None,
    updated_input: dict | None = None,
    continue_: bool | None = None,
) -> Decision:
    return Decision(
        decision=verdict,
        reason_id=reason_id,
        reason=reason,
        additional_context=additional_context,
        updated_input=updated_input,
        continue_=continue_,
    )


# --------------------------------------------------------------------------- #
# permission family (PreToolUse) — the cardinal no-bare-decision rule
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("verdict", ["allow", "deny", "ask"])
def test_pretooluse_maps_verdict_onto_permission_decision(verdict: str) -> None:
    wire = to_wire("PreToolUse", _decision(verdict))
    hso = wire["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == verdict
    _assert_valid(wire)


@pytest.mark.parametrize("verdict", ["allow", "deny", "ask"])
def test_pretooluse_never_emits_bare_top_level_decision(verdict: str) -> None:
    wire = to_wire("PreToolUse", _decision(verdict))
    assert "decision" not in wire


def test_pretooluse_unrecognized_internal_decision_is_deny() -> None:
    # Watch Out #15: an unknown internal verdict maps to deny, not pass-through.
    wire = to_wire("PreToolUse", _decision("bogus-verdict"))
    assert wire["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "decision" not in wire
    _assert_valid(wire)


def test_pretooluse_empty_internal_decision_is_deny() -> None:
    # Watch Out #15: an empty-string verdict maps to deny.
    wire = to_wire("PreToolUse", _decision(""))
    assert wire["hookSpecificOutput"]["permissionDecision"] == "deny"
    _assert_valid(wire)


def test_pretooluse_includes_reason_with_reason_id_prefix() -> None:
    wire = to_wire("PreToolUse", _decision("deny", reason_id="PC-001", reason="nope"))
    assert wire["hookSpecificOutput"]["permissionDecisionReason"] == "[PC-001] nope"


def test_pretooluse_reason_without_reason_id_is_plain() -> None:
    wire = to_wire("PreToolUse", _decision("allow", reason_id="", reason="plain"))
    assert wire["hookSpecificOutput"]["permissionDecisionReason"] == "plain"


def test_pretooluse_empty_reason_omits_reason_key() -> None:
    wire = to_wire("PreToolUse", _decision("allow", reason_id="", reason=""))
    assert "permissionDecisionReason" not in wire["hookSpecificOutput"]
    _assert_valid(wire)


def test_pretooluse_carries_updated_input_and_additional_context() -> None:
    wire = to_wire(
        "PreToolUse",
        _decision(
            "ask",
            updated_input={"filePath": "/tmp/x"},
            additional_context="extra ctx",
        ),
    )
    hso = wire["hookSpecificOutput"]
    assert hso["updatedInput"] == {"filePath": "/tmp/x"}
    assert hso["additionalContext"] == "extra ctx"
    _assert_valid(wire)


# --------------------------------------------------------------------------- #
# block family (PostToolUse / Stop / SubagentStop)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("event", ["PostToolUse", "Stop", "SubagentStop"])
def test_block_family_deny_uses_top_level_block(event: str) -> None:
    wire = to_wire(event, _decision("deny", reason_id="RV-001", reason="residual"))
    assert wire["decision"] == "block"
    assert wire["reason"] == "[RV-001] residual"
    assert "permissionDecision" not in wire
    _assert_valid(wire)


def test_block_family_allow_is_empty_object() -> None:
    wire = to_wire("Stop", _decision("allow"))
    assert wire == {}
    _assert_valid(wire)


def test_block_family_additional_context_rides_hook_specific_output() -> None:
    wire = to_wire(
        "Stop",
        _decision("deny", reason_id="RV-001", reason="r", additional_context="reroute"),
    )
    assert wire["hookSpecificOutput"] == {
        "hookEventName": "Stop",
        "additionalContext": "reroute",
    }
    _assert_valid(wire)


def test_block_family_continue_false_marks_non_recoverable_stop() -> None:
    wire = to_wire(
        "Stop",
        _decision("deny", reason_id="ST-901", reason="user stop", continue_=False),
    )
    assert wire["continue"] is False
    assert wire["stopReason"] == "user stop"
    _assert_valid(wire)


def test_block_family_recoverable_stop_omits_continue() -> None:
    wire = to_wire("Stop", _decision("deny", reason_id="RV-002", reason="r"))
    assert "continue" not in wire


# --------------------------------------------------------------------------- #
# common family (SessionStart / SubagentStart / UserPromptSubmit / PreCompact)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "event", ["SessionStart", "SubagentStart", "UserPromptSubmit"]
)
def test_common_allow_is_empty_object(event: str) -> None:
    wire = to_wire(event, _decision("allow"))
    assert wire == {}
    _assert_valid(wire)


def test_precompact_allow_emits_continue_true() -> None:
    wire = to_wire("PreCompact", _decision("allow"))
    assert wire == {"continue": True}
    _assert_valid(wire)


def test_common_deny_emits_system_message_only() -> None:
    wire = to_wire("UserPromptSubmit", _decision("deny", reason_id="PC-009", reason="x"))
    assert wire == {"systemMessage": "[PC-009] x"}
    _assert_valid(wire)


def test_common_deny_continue_false_emits_stop_shape() -> None:
    wire = to_wire(
        "SessionStart",
        _decision("deny", reason_id="PC-009", reason="halt", continue_=False),
    )
    assert wire["continue"] is False
    assert wire["stopReason"] == "halt"
    assert wire["systemMessage"] == "[PC-009] halt"
    _assert_valid(wire)


# --------------------------------------------------------------------------- #
# fail-closed path (Watch Out #15) — unknown event / None decision
# --------------------------------------------------------------------------- #
def test_none_decision_fails_closed_to_cross_family_deny() -> None:
    wire = to_wire("PreToolUse", None)
    assert wire["decision"] == "block"
    assert wire["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "fail-closed" in wire["reason"]
    _assert_valid(wire)


def test_unrecognized_event_fails_closed_with_event_name() -> None:
    wire = to_wire("Bogus", _decision("allow"))
    assert wire["decision"] == "block"
    assert wire["hookSpecificOutput"]["hookEventName"] == "Bogus"
    assert wire["hookSpecificOutput"]["permissionDecision"] == "deny"
    _assert_valid(wire)


def test_empty_event_name_fails_closed_as_unknown() -> None:
    wire = to_wire("", _decision("deny", reason_id="PC-004", reason="parse"))
    assert wire["hookSpecificOutput"]["hookEventName"] == "UNKNOWN"
    assert wire["reason"] == "[PC-004] parse"
    _assert_valid(wire)


def test_non_string_event_fails_closed_as_unknown() -> None:
    wire = to_wire(123, _decision("allow"))  # type: ignore[arg-type]
    assert wire["hookSpecificOutput"]["hookEventName"] == "UNKNOWN"
    assert wire["hookSpecificOutput"]["permissionDecision"] == "deny"
    _assert_valid(wire)


def test_none_event_and_none_decision_fails_closed() -> None:
    wire = to_wire(None, None)
    assert wire["decision"] == "block"
    assert wire["hookSpecificOutput"]["hookEventName"] == "UNKNOWN"
    _assert_valid(wire)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
