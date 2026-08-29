"""Tests for the decision emitter (spec015 Task 8.2 / 8.5).

The emitter is a thin composition of the pipeline decision and the wire adapter.
These tests confirm it delegates to the adapter, serializes compact JSON, fails
closed on a ``None`` decision via the real ``to_wire`` default, and that the
emitted shapes validate against ``hook-wire-output.schema.v1.json`` through the
stdlib ``_jsonschema_lite`` validator.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from helm_controller.contracts._jsonschema_lite import compile_schema
from helm_controller.contracts.decision import Decision
from helm_controller.hooks.decision_emitter import DecisionEmitter


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


def _decision(verdict: str) -> Decision:
    return Decision(decision=verdict, reason_id="PC-001", reason="reason")


def test_emit_uses_injected_adapter() -> None:
    captured: list[tuple] = []

    def fake_adapter(event, decision):
        captured.append((event, decision))
        return {"decision": "block", "reason": "stub"}

    emitter = DecisionEmitter(adapter=fake_adapter)
    wire = emitter.emit("Stop", _decision("deny"))
    assert wire == {"decision": "block", "reason": "stub"}
    assert captured == [("Stop", _decision("deny"))]


def test_emit_default_adapter_produces_permission_wire() -> None:
    emitter = DecisionEmitter()
    wire = emitter.emit("PreToolUse", _decision("deny"))
    assert wire["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "decision" not in wire
    _assert_valid(wire)


def test_emit_none_decision_fails_closed() -> None:
    emitter = DecisionEmitter()
    wire = emitter.emit("PreToolUse", None)
    assert wire["decision"] == "block"
    assert wire["hookSpecificOutput"]["permissionDecision"] == "deny"
    _assert_valid(wire)


def test_emit_json_is_compact_serialization() -> None:
    emitter = DecisionEmitter()
    payload = emitter.emit_json("Stop", _decision("deny"))
    assert ", " not in payload
    assert ": " not in payload
    assert json.loads(payload) == emitter.emit("Stop", _decision("deny"))


def test_emit_json_round_trips_to_valid_wire() -> None:
    emitter = DecisionEmitter()
    payload = emitter.emit_json("PreToolUse", _decision("allow"))
    _assert_valid(json.loads(payload))


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
