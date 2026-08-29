"""Conditional check evaluators for COND matrix outcomes (spec015 Task 4.3).

Three check types defined in this phase:

* ``subagent_target_check`` — validates the dispatch target role is
  permitted for the active agent role.  Emits ``PC-002`` on failure.

* ``scr_path_check`` — validates no extracted path is under
  ``<workspace>/.scr/``.  Emits ``PC-003`` on failure or when paths
  cannot be determined (path-unknown → deny by default per plan F-015).

* ``scoped_path_check`` — validates extracted paths are contained within
  the workspace root.  Role-specific narrowing is added in Phase 6
  invariants (INV layer).  Emits ``PC-003`` on failure.

Entry point: :func:`run_conditional_checks`.
Individual check functions are public for direct unit-test invocation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from helm_controller.policy.tool_classes import ToolClassMap

PC_002 = "PC-002"
PC_003 = "PC-003"


class ConditionalCheckError(Exception):
    """Raised when an unknown check type is requested (programming error)."""


@dataclass(frozen=True)
class ConditionalCheckResult:
    passed: bool
    reason_id: str | None
    reason: str | None


# ---------------------------------------------------------------------------
# Subagent target check
# ---------------------------------------------------------------------------

# Permitted dispatch target roles per active role.
# Roles absent from this mapping have no dispatch permission (DENY in matrix).
_ALLOWED_TARGET_ROLES: dict[str, frozenset[str]] = {
    "orchestrator": frozenset(
        {
            "orchestrator",
            "clarifier",
            "planner",
            "researcher",
            "writer",
            "recruiter",
            "tester",
            "auditor",
            "implementer",
            "reviewer",
        }
    ),
    "planner": frozenset({"researcher"}),
    "recruiter": frozenset({"researcher"}),
    "tester": frozenset(
        {"orchestrator", "researcher", "planner", "writer", "recruiter"}
    ),
}


def check_subagent_target(
    role: str,
    tool_input: dict[str, Any] | None,
    resolve_role: Callable[[str], str],
) -> ConditionalCheckResult:
    """Check that the dispatch target agent's role is permitted for *role*.

    *tool_input* must carry an ``"agent"`` key with the target agent name.
    Returns ``PC-002`` on failure or when inputs are invalid/missing.
    """
    if tool_input is None:
        return ConditionalCheckResult(
            passed=False,
            reason_id=PC_002,
            reason="subagent_target_check: tool_input is None",
        )
    agent = tool_input.get("agent")
    if not agent:
        return ConditionalCheckResult(
            passed=False,
            reason_id=PC_002,
            reason="subagent_target_check: tool_input missing 'agent' field",
        )
    allowed = _ALLOWED_TARGET_ROLES.get(role)
    if allowed is None:
        return ConditionalCheckResult(
            passed=False,
            reason_id=PC_002,
            reason=f"subagent_target_check: role '{role}' has no dispatch permissions",
        )
    target_role = resolve_role(str(agent))
    if target_role in allowed:
        return ConditionalCheckResult(passed=True, reason_id=None, reason=None)
    return ConditionalCheckResult(
        passed=False,
        reason_id=PC_002,
        reason=(
            f"subagent_target_check: agent '{agent}' has role '{target_role}'"
            f" which is not permitted for active role '{role}'"
        ),
    )


# ---------------------------------------------------------------------------
# Path extraction helper
# ---------------------------------------------------------------------------


def _extract_paths(
    path_fields: tuple[str, ...],
    tool_input: dict[str, Any] | None,
) -> list[str] | None:
    """Extract path strings from *tool_input* using *path_fields* annotations.

    Returns ``None`` when any path cannot be determined (invalid inputs or
    a missing/wrong-type field).  Returns an empty list only when
    *path_fields* is empty (path-unknown — callers must deny with PC-003).
    """
    if tool_input is None:
        return None
    paths: list[str] = []
    for field_spec in path_fields:
        if "[*]." in field_spec:
            array_key, _, sub_key = field_spec.partition("[*].")
            items = tool_input.get(array_key)
            if not isinstance(items, list):
                return None
            for item in items:
                if not isinstance(item, dict):
                    return None
                val = item.get(sub_key)
                if not isinstance(val, str):
                    return None
                paths.append(val)
        else:
            val = tool_input.get(field_spec)
            if not isinstance(val, str):
                return None
            paths.append(val)
    return paths


# ---------------------------------------------------------------------------
# .scr/ path restriction check  (PC-003, plan F-015 resolution)
# ---------------------------------------------------------------------------


def check_scr_path(
    tool_name: str,
    tool_input: dict[str, Any] | None,
    workspace_root: str,
    tool_class_map: ToolClassMap,
) -> ConditionalCheckResult:
    """Deny any file_mutation path under ``<workspace_root>/.scr/``.

    Uses the ``path_fields`` annotation from *tool_class_map* to locate
    path values in *tool_input*.  A tool with no annotation (empty
    path_fields) is treated as path-unknown and denied with ``PC-003``
    per plan F-015.  Path comparison uses ``Path.resolve()`` to handle
    backslash/forward-slash variants and relative paths on all platforms.
    """
    entry = tool_class_map.classify(tool_name)
    path_fields = entry.path_fields
    if not path_fields:
        return ConditionalCheckResult(
            passed=False,
            reason_id=PC_003,
            reason=(
                f"scr_path_check: tool '{tool_name}' has no path_fields annotation"
                " — write path unknown, denied by default"
            ),
        )
    paths = _extract_paths(path_fields, tool_input)
    if paths is None:
        return ConditionalCheckResult(
            passed=False,
            reason_id=PC_003,
            reason=(
                f"scr_path_check: could not extract paths from tool_input"
                f" for tool '{tool_name}'"
            ),
        )
    scr_root = (Path(workspace_root) / ".scr").resolve()
    for raw_path in paths:
        resolved = Path(raw_path).resolve()
        try:
            resolved.relative_to(scr_root)
            # Path IS under .scr/ — deny
            return ConditionalCheckResult(
                passed=False,
                reason_id=PC_003,
                reason=(
                    f"scr_path_check: path '{raw_path}' is under"
                    f" .scr/ — direct writes to .scr/ are denied (PC-003)"
                ),
            )
        except ValueError:
            pass  # not relative to .scr/ — OK
    return ConditionalCheckResult(passed=True, reason_id=None, reason=None)


# ---------------------------------------------------------------------------
# Scoped path check (workspace-containment; Phase 4 baseline)
# ---------------------------------------------------------------------------


def check_scoped_path(
    tool_name: str,
    tool_input: dict[str, Any] | None,
    workspace_root: str,
    tool_class_map: ToolClassMap,
) -> ConditionalCheckResult:
    """Verify extracted paths stay within *workspace_root*.

    Phase 4 baseline: validates workspace containment only.  Role-specific
    path narrowing (clarifier output paths, auditor report exclusions,
    reviewer write restrictions) is added in Phase 6 INV invariants.
    """
    entry = tool_class_map.classify(tool_name)
    path_fields = entry.path_fields
    if not path_fields:
        return ConditionalCheckResult(
            passed=False,
            reason_id=PC_003,
            reason=(
                f"scoped_path_check: tool '{tool_name}' has no path_fields annotation"
                " — write path unknown, denied by default"
            ),
        )
    paths = _extract_paths(path_fields, tool_input)
    if paths is None:
        return ConditionalCheckResult(
            passed=False,
            reason_id=PC_003,
            reason=(
                f"scoped_path_check: could not extract paths from tool_input"
                f" for tool '{tool_name}'"
            ),
        )
    ws_root = Path(workspace_root).resolve()
    for raw_path in paths:
        resolved = Path(raw_path).resolve()
        try:
            resolved.relative_to(ws_root)
        except ValueError:
            return ConditionalCheckResult(
                passed=False,
                reason_id=PC_003,
                reason=(
                    f"scoped_path_check: path '{raw_path}' is outside"
                    f" workspace root '{workspace_root}' (PC-003)"
                ),
            )
    return ConditionalCheckResult(passed=True, reason_id=None, reason=None)


# ---------------------------------------------------------------------------
# Dispatcher and entry point
# ---------------------------------------------------------------------------

_CHECK_DISPATCH: dict[
    str,
    Callable[..., ConditionalCheckResult],
] = {
    "subagent_target_check": check_subagent_target,
    "scr_path_check": check_scr_path,
    "scoped_path_check": check_scoped_path,
}


def run_conditional_checks(
    check_types: tuple[str, ...],
    *,
    role: str,
    tool_name: str,
    tool_input: dict[str, Any] | None,
    workspace_root: str,
    tool_class_map: ToolClassMap,
    resolve_role: Callable[[str], str],
) -> ConditionalCheckResult:
    """Run *check_types* in sequence; short-circuit and return on first failure.

    Args:
        check_types: ordered tuple of check identifiers (from matrix result).
        role: active agent role resolved by the registry.
        tool_name: tool identifier being evaluated.
        tool_input: raw tool_input dict from the hook envelope.
        workspace_root: absolute path to the workspace root directory.
        tool_class_map: :class:`~helm_controller.policy.tool_classes.ToolClassMap`
            instance for path-field lookup.
        resolve_role: callable mapping an agent name to its role string.

    Returns:
        :class:`ConditionalCheckResult` — ``passed=True`` iff all checks pass.

    Raises:
        :class:`ConditionalCheckError`: if an unrecognised check type is
            requested (programming error, not a runtime policy failure).
    """
    for check_type in check_types:
        fn = _CHECK_DISPATCH.get(check_type)
        if fn is None:
            raise ConditionalCheckError(
                f"Unknown conditional check type: '{check_type}'"
            )
        if check_type == "subagent_target_check":
            result = fn(role, tool_input, resolve_role)
        else:
            result = fn(tool_name, tool_input, workspace_root, tool_class_map)

        if not result.passed:
            return result  # short-circuit

    return ConditionalCheckResult(passed=True, reason_id=None, reason=None)
