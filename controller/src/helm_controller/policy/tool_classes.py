"""Tool-identifier → policy-class mapping (spec015 Task 4.2).

Implements the seven policy classes from boundary contract Appendix B:
``read``, ``workflow_state``, ``agent_dispatch``, ``file_mutation``,
``web_external``, ``vscode_system``, ``execution``.

Unknown tool identifiers resolve to the ``UNKNOWN`` class and are denied
by default per the policy matrix.

``file_mutation`` entries carry ``path_fields`` annotations that the
conditional checks in :mod:`helm_controller.policy.conditional_checks`
use to extract paths from ``tool_input`` for ``.scr/`` path restriction
and scoped-path checks.

**Data-format note (deviation from plan):** The plan names
``tool_classes.yaml``; this module uses ``tool_classes.json`` for
stdlib compatibility.  See ``registry.py`` for the full rationale.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

UNKNOWN_CLASS = "UNKNOWN"

POLICY_CLASSES: frozenset[str] = frozenset(
    {
        "read",
        "workflow_state",
        "agent_dispatch",
        "file_mutation",
        "web_external",
        "vscode_system",
        "execution",
    }
)

_DEFAULT_DATA_FILE = Path(__file__).parent / "tool_classes.json"


class ToolClassError(Exception):
    """Raised when the tool_classes data file cannot be read or parsed."""


@dataclass(frozen=True)
class ToolEntry:
    name: str
    policy_class: str
    path_fields: tuple[str, ...] = field(default_factory=tuple)


def _load_class_map(path: Path) -> dict[str, ToolEntry]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ToolClassError(
            f"Cannot read tool_classes data file '{path}': {exc}"
        ) from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ToolClassError(
            f"Malformed JSON in tool_classes data file '{path}': {exc}"
        ) from exc
    classes = data.get("classes")
    if not isinstance(classes, dict):
        raise ToolClassError(
            f"tool_classes data file '{path}' missing top-level 'classes' dict"
        )
    result: dict[str, ToolEntry] = {}
    for cls_name, entries in classes.items():
        if not isinstance(entries, list):
            raise ToolClassError(
                f"Class '{cls_name}' in '{path}' must be a list of entries"
            )
        for entry in entries:
            if isinstance(entry, str):
                result[entry] = ToolEntry(name=entry, policy_class=cls_name)
            elif isinstance(entry, dict):
                name = entry.get("name")
                if not name:
                    raise ToolClassError(
                        f"Tool entry in class '{cls_name}' in '{path}' missing 'name'"
                    )
                path_fields = tuple(entry.get("path_fields") or [])
                result[str(name)] = ToolEntry(
                    name=str(name),
                    policy_class=cls_name,
                    path_fields=path_fields,
                )
            else:
                raise ToolClassError(
                    f"Invalid entry type {type(entry).__name__!r} in class"
                    f" '{cls_name}' in '{path}'"
                )
    return result


class ToolClassMap:
    """Maps tool identifiers to their policy class and path-field annotations.

    Args:
        data_file: Path to the JSON data file.  Defaults to the bundled
            ``tool_classes.json`` alongside this module.
    """

    def __init__(self, data_file: Path | None = None) -> None:
        self._map: dict[str, ToolEntry] = _load_class_map(
            data_file or _DEFAULT_DATA_FILE
        )

    def classify(self, tool_name: str) -> ToolEntry:
        """Return the :class:`ToolEntry` for *tool_name*.

        Returns an entry with ``policy_class == UNKNOWN_CLASS`` when the
        tool is not registered.
        """
        return self._map.get(
            tool_name, ToolEntry(name=tool_name, policy_class=UNKNOWN_CLASS)
        )

    def known_tools(self) -> frozenset[str]:
        """Return all registered tool names."""
        return frozenset(self._map)
