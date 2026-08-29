"""Transcript reader for residual parity audits (spec015 Task 8.4).

Reads the JSONL transcript referenced by the hook envelope's ``transcript_path``
and normalizes each line into a :class:`TranscriptEvent`. The reader is the sole
owner of the failure modes the residual checks must distinguish:

* the transcript file is absent (``PC-008`` — transcript unavailable),
* a line is not valid JSON (malformed transcript),
* the transcript has no usable lines (empty transcript),
* a line carries an event type the scanner does not recognize (classified as
  ``unknown`` rather than dropped, so the residual scan stays total).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

ASSISTANT_MESSAGE = "assistant_message"
USER_MESSAGE = "user_message"
TOOL_CALL = "tool_call"
TOOL_RESULT = "tool_result"
UNKNOWN = "unknown"

_TYPE_ALIASES: dict[str, str] = {
    "assistant": ASSISTANT_MESSAGE,
    "assistant_message": ASSISTANT_MESSAGE,
    "user": USER_MESSAGE,
    "user_message": USER_MESSAGE,
    "tool_call": TOOL_CALL,
    "tool_use": TOOL_CALL,
    "tool_result": TOOL_RESULT,
    "tool_response": TOOL_RESULT,
}


class TranscriptUnavailableError(FileNotFoundError):
    """The transcript file does not exist or cannot be opened (``PC-008``)."""


class MalformedTranscriptError(ValueError):
    """A transcript line is not parseable as JSON."""


class EmptyTranscriptError(ValueError):
    """The transcript contains no non-blank lines."""


@dataclass(frozen=True)
class TranscriptEvent:
    """One normalized transcript line."""

    event_type: str
    text: str
    tool_name: str | None
    raw: dict


def _classify(obj: dict) -> str:
    raw_type = obj.get("type") or obj.get("event") or obj.get("role")
    if not isinstance(raw_type, str):
        return UNKNOWN
    return _TYPE_ALIASES.get(raw_type, UNKNOWN)


def _to_event(obj: dict) -> TranscriptEvent:
    text = obj.get("text") or obj.get("content") or ""
    tool_name = obj.get("tool_name") or obj.get("name")
    return TranscriptEvent(
        event_type=_classify(obj),
        text=text if isinstance(text, str) else "",
        tool_name=tool_name if isinstance(tool_name, str) else None,
        raw=obj,
    )


def _iter_lines(path: Path) -> Iterator[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise TranscriptUnavailableError(
            f"transcript not found: {path}"
        ) from exc
    yield from (line for line in text.splitlines() if line.strip())


def read_transcript(transcript_path: str) -> list[TranscriptEvent]:
    """Read and normalize *transcript_path* into a list of transcript events."""
    path = Path(transcript_path)
    lines = list(_iter_lines(path))
    if not lines:
        raise EmptyTranscriptError(f"transcript is empty: {path}")
    events: list[TranscriptEvent] = []
    for line in lines:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise MalformedTranscriptError(
                f"malformed transcript line in {path}: {exc}"
            ) from exc
        if not isinstance(obj, dict):
            raise MalformedTranscriptError(
                f"transcript line is not a JSON object in {path}"
            )
        events.append(_to_event(obj))
    return events
