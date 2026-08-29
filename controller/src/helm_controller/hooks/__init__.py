"""Controller-side hook payload parsing and normalization (Phase 3).

Re-exports the parser entry point, the normalized record, and the field-map
table so callers import from one place::

    from helm_controller.hooks import parse, ParsedHook
    parsed = parse(raw_payload)
"""

from __future__ import annotations

from helm_controller.hooks.field_map import (
    FIELD_MAP,
    FieldMapError,
    get_field,
    to_source,
)
from helm_controller.hooks.parsers import (
    EVENT_FIELDS,
    HookParseError,
    ParsedHook,
    parse,
)

__all__ = [
    "EVENT_FIELDS",
    "FIELD_MAP",
    "FieldMapError",
    "HookParseError",
    "ParsedHook",
    "get_field",
    "parse",
    "to_source",
]
