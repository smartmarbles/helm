"""100%-branch tests for the controller-side hook parsers and field map (Task 3.1)."""

from __future__ import annotations

import pytest

from helm_controller.hooks import field_map, parsers
from helm_controller.hooks.field_map import FieldMapError
from helm_controller.hooks.parsers import EVENT_FIELDS, HookParseError, parse


def _common(event: str) -> dict:
    return {
        "hookEventName": event,
        "sessionId": "sess-1",
        "timestamp": "2026-05-31T00:00:00Z",
        "cwd": "/ws",
        "transcript_path": "/ws/.transcript.jsonl",
    }


# --- field_map ------------------------------------------------------------


def test_to_source_maps_camelcase_identity_fields() -> None:
    assert field_map.to_source("session_id") == "sessionId"
    assert field_map.to_source("hook_event") == "hookEventName"


def test_to_source_falls_back_to_identity_for_passthrough_fields() -> None:
    assert field_map.to_source("tool_name") == "tool_name"
    assert field_map.to_source("agent_id") == "agent_id"


def test_get_field_known_camelcase_lookup() -> None:
    payload = {"sessionId": "s-9", "hookEventName": "Stop"}
    assert field_map.get_field(payload, "session_id") == "s-9"
    assert field_map.get_field(payload, "hook_event") == "Stop"


def test_get_field_known_snakecase_passthrough_lookup() -> None:
    assert field_map.get_field({"tool_name": "edit"}, "tool_name") == "edit"


def test_get_field_absent_optional_returns_none() -> None:
    assert field_map.get_field({}, "tool_name") is None


def test_get_field_absent_required_raises() -> None:
    with pytest.raises(FieldMapError, match="missing required field: sessionId"):
        field_map.get_field({}, "session_id", required=True)


def test_get_field_present_required_returns_value() -> None:
    assert field_map.get_field({"sessionId": "x"}, "session_id", required=True) == "x"


# --- parsers: all eight events --------------------------------------------


def test_parse_pre_tool_use() -> None:
    payload = _common("PreToolUse") | {
        "tool_name": "edit_file",
        "tool_input": {"path": "a.py"},
        "tool_use_id": "tu-1",
    }
    parsed = parse(payload)
    assert parsed.hook_event == "PreToolUse"
    assert parsed.session_id == "sess-1"
    assert parsed.timestamp == "2026-05-31T00:00:00Z"
    assert parsed.cwd == "/ws"
    assert parsed.transcript_path == "/ws/.transcript.jsonl"
    assert parsed.tool_name == "edit_file"
    assert parsed.tool_input == {"path": "a.py"}
    assert parsed.tool_use_id == "tu-1"
    assert parsed.tool_response is None


def test_parse_post_tool_use() -> None:
    payload = _common("PostToolUse") | {
        "tool_name": "edit_file",
        "tool_input": {"path": "a.py"},
        "tool_use_id": "tu-1",
        "tool_response": {"ok": True},
    }
    parsed = parse(payload)
    assert parsed.hook_event == "PostToolUse"
    assert parsed.tool_response == {"ok": True}


def test_parse_subagent_start() -> None:
    parsed = parse(_common("SubagentStart") | {"agent_id": "a-1", "agent_type": "FORGE"})
    assert parsed.agent_id == "a-1"
    assert parsed.agent_type == "FORGE"


def test_parse_subagent_stop() -> None:
    parsed = parse(_common("SubagentStop") | {"stop_hook_active": True})
    assert parsed.stop_hook_active is True


def test_parse_stop() -> None:
    parsed = parse(_common("Stop") | {"stop_hook_active": False})
    assert parsed.hook_event == "Stop"
    assert parsed.stop_hook_active is False


def test_parse_session_start() -> None:
    parsed = parse(_common("SessionStart") | {"source": "new"})
    assert parsed.source == "new"


def test_parse_user_prompt_submit() -> None:
    parsed = parse(_common("UserPromptSubmit") | {"prompt": "do the thing"})
    assert parsed.prompt == "do the thing"


def test_parse_pre_compact() -> None:
    parsed = parse(_common("PreCompact") | {"trigger": "auto"})
    assert parsed.trigger == "auto"


def test_event_fields_table_covers_all_eight_events() -> None:
    assert set(EVENT_FIELDS) == {
        "PreToolUse",
        "PostToolUse",
        "SubagentStart",
        "SubagentStop",
        "Stop",
        "SessionStart",
        "UserPromptSubmit",
        "PreCompact",
    }


# --- parsers: optional/extra/missing/malformed -----------------------------


def test_parse_missing_event_specific_fields_default_to_none() -> None:
    parsed = parse(_common("PreToolUse"))
    assert parsed.tool_name is None
    assert parsed.tool_input is None
    assert parsed.tool_use_id is None


def test_parse_missing_common_optional_fields_default_to_none() -> None:
    parsed = parse({"hookEventName": "Stop", "sessionId": "s-2"})
    assert parsed.timestamp is None
    assert parsed.cwd is None
    assert parsed.transcript_path is None


def test_parse_ignores_extra_unmapped_fields() -> None:
    parsed = parse(_common("Stop") | {"unexpected": "ignored", "stop_hook_active": True})
    assert parsed.stop_hook_active is True
    assert not hasattr(parsed, "unexpected")


def test_parse_non_dict_payload_raises() -> None:
    with pytest.raises(HookParseError, match="must be a JSON object"):
        parse(["not", "a", "dict"])


def test_parse_missing_hook_event_raises() -> None:
    with pytest.raises(HookParseError, match="missing required field: hookEventName"):
        parse({"sessionId": "s-1"})


def test_parse_missing_session_id_raises() -> None:
    with pytest.raises(HookParseError, match="missing required field: sessionId"):
        parse({"hookEventName": "PreToolUse"})


def test_parse_unrecognized_event_raises() -> None:
    with pytest.raises(HookParseError, match="unrecognized hook event"):
        parse({"hookEventName": "NotAnEvent", "sessionId": "s-1"})
