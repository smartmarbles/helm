"""Raw hook-payload parsers for all eight Copilot events (Task 3.1).

This is the CONTROLLER-side normalization layer: it turns the per-event stdin
payload VS Code Copilot delivers (already JSON-decoded by the transport) into a
flat, internally-named :class:`ParsedHook`. It applies the
:mod:`~helm_controller.hooks.field_map` table (``sessionId`` -> ``session_id``,
``hookEventName`` -> ``hook_event``; all other fields pass through verbatim) and
extracts only the per-event fields documented in ``phase3-hook-verification.md``
Finding 3.

Scope boundary: parsing only. Workflow/blackboard context and the active-agent
lookup that complete a :class:`~helm_controller.contracts.envelope.Envelope` are
added by the envelope assembler (Task 3.3), which reads the runtime store; the
internal decision vocabulary stays ``allow``/``deny``/``ask`` and the VS Code
wire adapter is Task 8.2 (Plan Decisions §D2). The tool-bearing fields are named
to match :class:`~helm_controller.contracts.envelope.ToolAttempt` so the
assembler maps them without renaming.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from helm_controller.hooks import field_map

#: Per-event field names to extract beyond the common fields. The event name is
#: the PascalCase ``hookEventName`` value as it arrives on the wire; the values
#: are internal field names resolved through :mod:`field_map`. Verified against
#: phase3-hook-verification.md Finding 3 (2026-05-28).
EVENT_FIELDS: dict[str, tuple[str, ...]] = {
    "PreToolUse": ("tool_name", "tool_input", "tool_use_id"),
    "PostToolUse": ("tool_name", "tool_input", "tool_use_id", "tool_response"),
    "SubagentStart": ("agent_id", "agent_type"),
    "SubagentStop": ("stop_hook_active",),
    "Stop": ("stop_hook_active",),
    "SessionStart": ("source",),
    "UserPromptSubmit": ("prompt",),
    "PreCompact": ("trigger",),
}


class HookParseError(ValueError):
    """Raised when a raw hook payload cannot be normalized."""


@dataclass(frozen=True)
class ParsedHook:
    """Normalized fields extracted from one raw hook payload.

    ``hook_event`` and ``session_id`` are guaranteed present; every other field
    is ``None`` unless the originating event carries it (per :data:`EVENT_FIELDS`).
    """

    hook_event: str
    session_id: str
    timestamp: str | None
    cwd: str | None
    transcript_path: str | None
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_use_id: str | None = None
    tool_response: dict[str, Any] | None = None
    agent_id: str | None = None
    agent_type: str | None = None
    stop_hook_active: bool | None = None
    source: str | None = None
    trigger: str | None = None
    prompt: str | None = None


def parse(payload: Any) -> ParsedHook:
    """Normalize one JSON-decoded hook payload into a :class:`ParsedHook`.

    Raises :class:`HookParseError` when the payload is not a JSON object, is
    missing the ``hookEventName``/``sessionId`` identity fields, or names an
    unrecognized event.
    """
    if not isinstance(payload, dict):
        raise HookParseError(
            f"payload must be a JSON object, got {type(payload).__name__}"
        )
    try:
        hook_event = field_map.get_field(payload, "hook_event", required=True)
        session_id = field_map.get_field(payload, "session_id", required=True)
    except field_map.FieldMapError as exc:
        raise HookParseError(str(exc)) from exc
    if hook_event not in EVENT_FIELDS:
        raise HookParseError(f"unrecognized hook event: {hook_event!r}")
    extras = {
        name: field_map.get_field(payload, name)
        for name in EVENT_FIELDS[hook_event]
    }
    return ParsedHook(
        hook_event=hook_event,
        session_id=session_id,
        timestamp=field_map.get_field(payload, "timestamp"),
        cwd=field_map.get_field(payload, "cwd"),
        transcript_path=field_map.get_field(payload, "transcript_path"),
        **extras,
    )
