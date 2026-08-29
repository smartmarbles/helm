"""Tests for the transcript reader (spec015 Task 8.4 / 8.5).

Covers the four failure modes the reader owns (missing file, malformed JSON,
empty transcript, non-object line) plus normalization branches: event-type
classification (known alias, unknown string, non-string, absent) and field
extraction (text/content fallback, tool_name/name fallback, non-string coercion).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from helm_controller.residual.transcript_reader import (
    ASSISTANT_MESSAGE,
    TOOL_CALL,
    UNKNOWN,
    USER_MESSAGE,
    EmptyTranscriptError,
    MalformedTranscriptError,
    TranscriptUnavailableError,
    read_transcript,
)


def _write(tmp_path: Path, *objs: object, name: str = "t.jsonl") -> str:
    path = tmp_path / name
    path.write_text(
        "\n".join(json.dumps(o) if not isinstance(o, str) else o for o in objs),
        encoding="utf-8",
    )
    return str(path)


# --------------------------------------------------------------------------- #
# failure modes
# --------------------------------------------------------------------------- #
def test_missing_file_raises_unavailable(tmp_path: Path) -> None:
    with pytest.raises(TranscriptUnavailableError):
        read_transcript(str(tmp_path / "nope.jsonl"))


def test_malformed_json_line_raises(tmp_path: Path) -> None:
    path = _write(tmp_path, "{not valid json")
    with pytest.raises(MalformedTranscriptError):
        read_transcript(path)


def test_non_object_line_raises(tmp_path: Path) -> None:
    path = _write(tmp_path, "[1, 2, 3]")
    with pytest.raises(MalformedTranscriptError):
        read_transcript(path)


def test_blank_only_transcript_is_empty(tmp_path: Path) -> None:
    path = _write(tmp_path, "", "   ", "\t")
    with pytest.raises(EmptyTranscriptError):
        read_transcript(path)


# --------------------------------------------------------------------------- #
# classification branches
# --------------------------------------------------------------------------- #
def test_known_type_aliases_normalized(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        {"type": "assistant", "text": "hi"},
        {"role": "user", "content": "yo"},
        {"event": "tool_use", "name": "runSubagent"},
    )
    events = read_transcript(path)
    assert [e.event_type for e in events] == [
        ASSISTANT_MESSAGE,
        USER_MESSAGE,
        TOOL_CALL,
    ]


def test_unknown_string_type_is_unknown(tmp_path: Path) -> None:
    path = _write(tmp_path, {"type": "telepathy", "text": "x"})
    assert read_transcript(path)[0].event_type == UNKNOWN


def test_non_string_type_is_unknown(tmp_path: Path) -> None:
    path = _write(tmp_path, {"type": 5, "text": "x"})
    assert read_transcript(path)[0].event_type == UNKNOWN


def test_absent_type_is_unknown(tmp_path: Path) -> None:
    path = _write(tmp_path, {"text": "x"})
    assert read_transcript(path)[0].event_type == UNKNOWN


# --------------------------------------------------------------------------- #
# field extraction branches
# --------------------------------------------------------------------------- #
def test_content_falls_back_when_text_absent(tmp_path: Path) -> None:
    path = _write(tmp_path, {"type": "assistant", "content": "from content"})
    assert read_transcript(path)[0].text == "from content"


def test_missing_text_defaults_to_empty(tmp_path: Path) -> None:
    path = _write(tmp_path, {"type": "assistant"})
    assert read_transcript(path)[0].text == ""


def test_non_string_text_coerced_to_empty(tmp_path: Path) -> None:
    path = _write(tmp_path, {"type": "assistant", "text": 42})
    assert read_transcript(path)[0].text == ""


def test_tool_name_uses_name_fallback(tmp_path: Path) -> None:
    path = _write(tmp_path, {"type": "tool_call", "name": "read_file"})
    assert read_transcript(path)[0].tool_name == "read_file"


def test_tool_name_prefers_tool_name_field(tmp_path: Path) -> None:
    path = _write(
        tmp_path, {"type": "tool_call", "tool_name": "grep", "name": "ignored"}
    )
    assert read_transcript(path)[0].tool_name == "grep"


def test_missing_tool_name_is_none(tmp_path: Path) -> None:
    path = _write(tmp_path, {"type": "assistant", "text": "x"})
    assert read_transcript(path)[0].tool_name is None


def test_non_string_tool_name_is_none(tmp_path: Path) -> None:
    path = _write(tmp_path, {"type": "tool_call", "tool_name": 7})
    assert read_transcript(path)[0].tool_name is None


def test_raw_object_preserved(tmp_path: Path) -> None:
    obj = {"type": "assistant", "text": "hi", "extra": 1}
    path = _write(tmp_path, obj)
    assert read_transcript(path)[0].raw == obj


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
