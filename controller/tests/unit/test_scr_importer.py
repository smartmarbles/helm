"""Unit tests for helm_controller.scr.importer and draft_parser (spec015 Task 11.5)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from helm_controller.contracts._jsonschema_lite import compile_schema
from helm_controller.scr.draft_parser import DraftParseError, parse
from helm_controller.scr.importer import import_draft
from helm_controller.scr.write_queue import ScrWriteQueue

_APPROVAL_SCHEMA = {
    "type": "object",
    "required": [
        "scr_schema_version",
        "record_class",
        "record_id",
        "workflow_id",
        "session_id",
        "turn_id",
        "created_at",
        "approved_by",
        "decision",
        "tool_name",
        "tool_use_id",
    ],
    "additionalProperties": False,
    "properties": {
        "scr_schema_version": {"type": "string", "const": "1"},
        "record_class": {"type": "string", "const": "approval"},
        "record_id": {"type": "string", "minLength": 1},
        "workflow_id": {"type": "string", "minLength": 1},
        "session_id": {"type": "string", "minLength": 1},
        "turn_id": {"type": "string", "minLength": 1},
        "created_at": {"type": "string", "minLength": 1},
        "approved_by": {"type": "string", "minLength": 1},
        "decision": {"type": "string", "enum": ["allow", "deny", "ask"]},
        "tool_name": {"type": "string", "minLength": 1},
        "tool_use_id": {"type": "string", "minLength": 1},
    },
}

_TRACE_SCHEMA = {
    "type": "object",
    "required": [
        "scr_schema_version",
        "record_class",
        "record_id",
        "workflow_id",
        "session_id",
        "turn_id",
        "created_at",
        "event_type",
        "fsm_state",
    ],
    "additionalProperties": False,
    "properties": {
        "scr_schema_version": {"type": "string", "const": "1"},
        "record_class": {"type": "string", "const": "trace"},
        "record_id": {"type": "string", "minLength": 1},
        "workflow_id": {"type": "string", "minLength": 1},
        "session_id": {"type": "string", "minLength": 1},
        "turn_id": {"type": "string", "minLength": 1},
        "created_at": {"type": "string", "minLength": 1},
        "event_type": {"type": "string", "minLength": 1},
        "fsm_state": {"type": "string", "minLength": 1},
        "transition_id": {"type": ["string", "null"]},
    },
}

_RUNTIME_MEMORY_SCHEMA = {
    "type": "object",
    "required": [
        "scr_schema_version",
        "record_class",
        "record_id",
        "workflow_id",
        "session_id",
        "turn_id",
        "created_at",
        "content",
        "agent_id",
    ],
    "additionalProperties": False,
    "properties": {
        "scr_schema_version": {"type": "string", "const": "1"},
        "record_class": {"type": "string", "const": "runtime_memory"},
        "record_id": {"type": "string", "minLength": 1},
        "workflow_id": {"type": "string", "minLength": 1},
        "session_id": {"type": "string", "minLength": 1},
        "turn_id": {"type": "string", "minLength": 1},
        "created_at": {"type": "string", "minLength": 1},
        "content": {"type": "string", "minLength": 1},
        "agent_id": {"type": "string", "minLength": 1},
    },
}


@pytest.fixture()
def schema_map() -> dict:
    return {
        "approval": compile_schema(_APPROVAL_SCHEMA),
        "trace": compile_schema(_TRACE_SCHEMA),
        "runtime_memory": compile_schema(_RUNTIME_MEMORY_SCHEMA),
    }


@pytest.fixture()
def queue_instance(tmp_path: Path, schema_map: dict) -> ScrWriteQueue:
    q = ScrWriteQueue(
        scr_root=tmp_path / ".scr",
        db_path=tmp_path / "test.db",
        schema_map=schema_map,
    )
    q.start()
    yield q
    q.stop()


def _write_draft(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


_VALID_APPROVAL_DRAFT = """\
---
record_class: approval
workflow_id: wf-abc
session_id: sess-1
turn_id: t-1
approved_by: ARTHUR
decision: allow
tool_name: create_file
tool_use_id: tu-001
---
Optional prose body.
"""

_VALID_TRACE_DRAFT = """\
---
record_class: trace
workflow_id: wf-xyz
session_id: sess-2
turn_id: t-2
event_type: EV-001
fsm_state: ST-010
---
"""

_VALID_RUNTIME_MEMORY_DRAFT = """\
---
record_class: runtime_memory
workflow_id: wf-mem
session_id: sess-3
turn_id: t-3
content: The plan is complete.
agent_id: ARTHUR
---
"""


# ---------------------------------------------------------------------------
# draft_parser unit tests
# ---------------------------------------------------------------------------


class TestDraftParser:
    def test_parses_valid_approval_draft(self, tmp_path: Path) -> None:
        p = _write_draft(tmp_path / "approval.md", _VALID_APPROVAL_DRAFT)
        result = parse(p)
        assert result["record_class"] == "approval"
        assert result["workflow_id"] == "wf-abc"
        assert result["decision"] == "allow"

    def test_parses_valid_trace_draft(self, tmp_path: Path) -> None:
        p = _write_draft(tmp_path / "trace.md", _VALID_TRACE_DRAFT)
        result = parse(p)
        assert result["record_class"] == "trace"
        assert result["fsm_state"] == "ST-010"

    def test_parses_valid_runtime_memory_draft(self, tmp_path: Path) -> None:
        p = _write_draft(tmp_path / "mem.md", _VALID_RUNTIME_MEMORY_DRAFT)
        result = parse(p)
        assert result["record_class"] == "runtime_memory"
        assert result["content"] == "The plan is complete."

    def test_missing_opening_delimiter_raises(self, tmp_path: Path) -> None:
        p = _write_draft(tmp_path / "bad.md", "no frontmatter here at all\nno dashes\n")
        with pytest.raises(DraftParseError, match="opening"):
            parse(p)

    def test_missing_closing_delimiter_raises(self, tmp_path: Path) -> None:
        p = _write_draft(tmp_path / "bad2.md", "---\nrecord_class: approval\n")
        with pytest.raises(DraftParseError, match="closing"):
            parse(p)

    def test_malformed_line_raises(self, tmp_path: Path) -> None:
        p = _write_draft(tmp_path / "bad3.md", "---\nno_colon_here\n---\n")
        with pytest.raises(DraftParseError, match="malformed"):
            parse(p)

    def test_blank_and_comment_lines_ignored(self, tmp_path: Path) -> None:
        content = "---\n# this is a comment\n\nrecord_class: trace\n---\n"
        p = _write_draft(tmp_path / "comment.md", content)
        result = parse(p)
        assert result == {"record_class": "trace"}

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        with pytest.raises(DraftParseError):
            parse(tmp_path / "nonexistent.md")

    def test_value_with_colon_preserved(self, tmp_path: Path) -> None:
        content = "---\ncontent: http://example.com/path\n---\n"
        p = _write_draft(tmp_path / "url.md", content)
        result = parse(p)
        assert result["content"] == "http://example.com/path"


# ---------------------------------------------------------------------------
# importer unit tests
# ---------------------------------------------------------------------------


class TestImporter:
    def test_valid_approval_draft_accepted(
        self, tmp_path: Path, queue_instance: ScrWriteQueue
    ) -> None:
        p = _write_draft(tmp_path / "approval.md", _VALID_APPROVAL_DRAFT)
        result = import_draft(p, queue_instance)
        assert result.success
        assert result.record_id is not None

    def test_valid_trace_draft_accepted(
        self, tmp_path: Path, queue_instance: ScrWriteQueue
    ) -> None:
        p = _write_draft(tmp_path / "trace.md", _VALID_TRACE_DRAFT)
        result = import_draft(p, queue_instance)
        assert result.success

    def test_valid_runtime_memory_draft_accepted(
        self, tmp_path: Path, queue_instance: ScrWriteQueue
    ) -> None:
        p = _write_draft(tmp_path / "mem.md", _VALID_RUNTIME_MEMORY_DRAFT)
        result = import_draft(p, queue_instance)
        assert result.success

    def test_missing_workflow_id_rejected(
        self, tmp_path: Path, queue_instance: ScrWriteQueue
    ) -> None:
        draft = """\
---
record_class: approval
session_id: sess-1
turn_id: t-1
approved_by: ARTHUR
decision: allow
tool_name: create_file
tool_use_id: tu-001
---
"""
        p = _write_draft(tmp_path / "missing_wf.md", draft)
        result = import_draft(p, queue_instance)
        assert not result.success
        assert result.error is not None

    def test_missing_record_class_rejected(
        self, tmp_path: Path, queue_instance: ScrWriteQueue
    ) -> None:
        draft = """\
---
workflow_id: wf-abc
session_id: sess-1
turn_id: t-1
---
"""
        p = _write_draft(tmp_path / "missing_class.md", draft)
        result = import_draft(p, queue_instance)
        assert not result.success
        assert "record_class" in result.error

    def test_unknown_record_class_rejected(
        self, tmp_path: Path, queue_instance: ScrWriteQueue
    ) -> None:
        draft = """\
---
record_class: unknown_class
workflow_id: wf-abc
session_id: sess-1
turn_id: t-1
---
"""
        p = _write_draft(tmp_path / "unknown_class.md", draft)
        result = import_draft(p, queue_instance)
        assert not result.success
        assert "unknown_class" in result.error

    def test_auto_generates_record_id(
        self, tmp_path: Path, queue_instance: ScrWriteQueue
    ) -> None:
        p = _write_draft(tmp_path / "approval.md", _VALID_APPROVAL_DRAFT)
        result = import_draft(p, queue_instance)
        assert result.success
        assert result.record_id and len(result.record_id) > 0

    def test_invalid_decision_value_rejected(
        self, tmp_path: Path, queue_instance: ScrWriteQueue
    ) -> None:
        draft = """\
---
record_class: approval
workflow_id: wf-abc
session_id: sess-1
turn_id: t-1
approved_by: ARTHUR
decision: BLOCK
tool_name: create_file
tool_use_id: tu-001
---
"""
        p = _write_draft(tmp_path / "bad_decision.md", draft)
        result = import_draft(p, queue_instance)
        assert not result.success

    def test_parse_failure_returns_write_result_false(
        self, tmp_path: Path, queue_instance: ScrWriteQueue
    ) -> None:
        p = _write_draft(tmp_path / "malformed.md", "---\nno_colon_here\n---\n")
        result = import_draft(p, queue_instance)
        assert not result.success
        assert result.error is not None

    def test_draft_with_prefilled_fields_accepted(
        self, tmp_path: Path, queue_instance: ScrWriteQueue
    ) -> None:
        draft = """\
---
record_class: approval
workflow_id: wf-abc
session_id: sess-1
turn_id: t-1
approved_by: ARTHUR
decision: allow
tool_name: create_file
tool_use_id: tu-001
record_id: r-prefilled
created_at: 2026-05-31T12:00:00+00:00
scr_schema_version: 1
---
"""
        p = _write_draft(tmp_path / "prefilled.md", draft)
        result = import_draft(p, queue_instance)
        assert result.success
        assert result.record_id == "r-prefilled"
