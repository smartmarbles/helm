"""Field-name mapping table for raw VS Code Copilot hook payloads (Task 3.1).

VS Code Copilot hook stdin payloads mix casing conventions: the chat-session
identifier is ``sessionId`` and the event name is ``hookEventName`` — both
camelCase — while every other field is snake_case (``tool_name``,
``transcript_path``, ``agent_id``, ``stop_hook_active``, …). This module is the
single authoritative source for that mapping (resolving spec §3.4 GAP-003 and
Watch Out #1), so parsers never hardcode a source key. The map is verified
against ``phase3-hook-verification.md`` Finding 3 (2026-05-28).
"""

from __future__ import annotations

from typing import Any

#: Internal field name -> raw hook-payload source key. Only entries whose source
#: key differs from the internal name need to appear; everything else falls back
#: to an identity lookup (the internal name IS the source key).
FIELD_MAP: dict[str, str] = {
    "session_id": "sessionId",
    "hook_event": "hookEventName",
}


class FieldMapError(KeyError):
    """Raised when a required field is missing from a hook payload."""


def to_source(internal_name: str) -> str:
    """Return the raw-payload source key for an internal field name.

    Unknown internal names fall back to themselves: most fields pass through
    verbatim (``tool_name``, ``agent_id``, …) and need no explicit map entry.
    """
    return FIELD_MAP.get(internal_name, internal_name)


def get_field(
    payload: dict[str, Any],
    internal_name: str,
    *,
    required: bool = False,
) -> Any:
    """Look up ``internal_name`` in ``payload`` via the field map.

    Returns ``None`` when the source key is absent and ``required`` is False.
    Raises :class:`FieldMapError` when the source key is absent and ``required``
    is True — the explicit exception path callers use for the identity fields
    (``sessionId``, ``hookEventName``) that must be present on every event.
    """
    source = to_source(internal_name)
    if source not in payload:
        if required:
            raise FieldMapError(f"missing required field: {source}")
        return None
    return payload[source]
