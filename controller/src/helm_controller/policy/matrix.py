"""Role-by-tool policy matrix evaluator (spec015 Task 4.3).

Implements the role × tool-class authorization table from boundary
contract §5.1.  Returns one of ``ALLOW`` / ``DENY`` / ``COND``.
Conditional outcomes carry a tuple of named follow-up checks that
:mod:`helm_controller.policy.conditional_checks` must evaluate before
the tool call is permitted.

Policy reason IDs emitted by this module:

* ``PC-001`` — agent-tool matrix violation (DENY outcome).

Conditional check IDs resolved downstream:

* ``PC-002`` — subagent target not permitted.
* ``PC-003`` — write-path scope violation.

**file_mutation promotion rule:** Per plan Task 4.3 F-015 resolution,
the ``.scr/`` path restriction check MUST run regardless of role, even
for roles that would otherwise ALLOW file writes.  Therefore, all
non-DENY ``file_mutation`` entries in this matrix are returned as
``COND`` carrying at minimum ``("scr_path_check",)``; there are no bare
``ALLOW`` outcomes for ``file_mutation``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

PC_001 = "PC-001"

UNKNOWN_ROLE = "UNKNOWN"
UNKNOWN_CLASS = "UNKNOWN"


class Verdict(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    COND = "COND"


@dataclass(frozen=True)
class MatrixResult:
    verdict: Verdict
    reason_id: str
    reason: str
    conditional_checks: tuple[str, ...] = field(default_factory=tuple)


# ------------------------------------------------------------------
# Policy matrix: (role, tool_class) → (Verdict, conditional_checks)
#
# Sourced from boundary contract §5.1, mapped onto the seven plan
# policy classes.  Column mapping:
#   agent/runSubagent → agent_dispatch
#   read + search     → read          (search absorbed; ALLOW if either ALLOW)
#   web               → web_external
#   edit              → file_mutation  (COND to force scr_path_check)
#   execute           → execution
#   todo              → vscode_system
#   memory            → workflow_state
# ------------------------------------------------------------------
_D: tuple[Verdict, tuple[str, ...]] = (Verdict.DENY, ())
_A: tuple[Verdict, tuple[str, ...]] = (Verdict.ALLOW, ())

_MATRIX: dict[str, dict[str, tuple[Verdict, tuple[str, ...]]]] = {
    "orchestrator": {
        "agent_dispatch": (Verdict.COND, ("subagent_target_check",)),
        "read": _A,
        "web_external": _D,
        "file_mutation": _D,
        "execution": _D,
        "vscode_system": _A,
        "workflow_state": _A,
    },
    "clarifier": {
        "agent_dispatch": _D,
        "read": _A,
        "web_external": _D,
        "file_mutation": (Verdict.COND, ("scoped_path_check", "scr_path_check")),
        "execution": _D,
        "vscode_system": _A,
        "workflow_state": _A,
    },
    "planner": {
        "agent_dispatch": (Verdict.COND, ("subagent_target_check",)),
        "read": _A,
        "web_external": _D,
        "file_mutation": (Verdict.COND, ("scr_path_check",)),
        "execution": _D,
        "vscode_system": _A,
        "workflow_state": _A,
    },
    "researcher": {
        "agent_dispatch": _D,
        "read": _A,
        "web_external": _A,
        "file_mutation": _D,
        "execution": _D,
        "vscode_system": _A,
        "workflow_state": _A,
    },
    "writer": {
        "agent_dispatch": _D,
        "read": _A,
        "web_external": _D,
        "file_mutation": (Verdict.COND, ("scr_path_check",)),
        "execution": _A,
        "vscode_system": _D,
        "workflow_state": _A,
    },
    "recruiter": {
        "agent_dispatch": (Verdict.COND, ("subagent_target_check",)),
        "read": _A,
        "web_external": _D,
        "file_mutation": (Verdict.COND, ("scr_path_check",)),
        "execution": _D,
        "vscode_system": _A,
        "workflow_state": _A,
    },
    "tester": {
        "agent_dispatch": (Verdict.COND, ("subagent_target_check",)),
        "read": _A,
        "web_external": _D,
        "file_mutation": (Verdict.COND, ("scr_path_check",)),
        "execution": _A,
        "vscode_system": _A,
        "workflow_state": _A,
    },
    "auditor": {
        "agent_dispatch": _D,
        "read": _A,
        "web_external": _D,
        "file_mutation": (Verdict.COND, ("scoped_path_check", "scr_path_check")),
        "execution": _D,
        "vscode_system": _A,
        "workflow_state": _A,
    },
    "implementer": {
        "agent_dispatch": _D,
        "read": _A,
        "web_external": _D,
        "file_mutation": (Verdict.COND, ("scr_path_check",)),
        "execution": _A,
        "vscode_system": _D,
        "workflow_state": _D,
    },
    "reviewer": {
        "agent_dispatch": _D,
        "read": _A,
        "web_external": _D,
        "file_mutation": (Verdict.COND, ("scoped_path_check", "scr_path_check")),
        "execution": _D,
        "vscode_system": _A,
        "workflow_state": _A,
    },
    UNKNOWN_ROLE: {
        "agent_dispatch": _D,
        "read": _A,
        "web_external": _D,
        "file_mutation": _D,
        "execution": _D,
        "vscode_system": _D,
        "workflow_state": _D,
    },
}


def evaluate(role: str, tool_class: str) -> MatrixResult:
    """Return the policy verdict for *role* attempting *tool_class*.

    Unknown roles fall back to the ``UNKNOWN`` row (deny all non-read).
    Unknown tool classes are denied with ``PC-001`` regardless of role.
    """
    role_row = _MATRIX.get(role)
    if role_row is None:
        role_row = _MATRIX[UNKNOWN_ROLE]

    entry = role_row.get(tool_class)
    if entry is None:
        return MatrixResult(
            verdict=Verdict.DENY,
            reason_id=PC_001,
            reason=f"unknown tool class '{tool_class}' denied by default",
        )

    verdict, cond_checks = entry
    if verdict == Verdict.ALLOW:
        return MatrixResult(
            verdict=Verdict.ALLOW,
            reason_id="",
            reason=f"tool class '{tool_class}' allowed for role '{role}'",
        )
    if verdict == Verdict.DENY:
        return MatrixResult(
            verdict=Verdict.DENY,
            reason_id=PC_001,
            reason=f"tool class '{tool_class}' not permitted for role '{role}'",
        )
    # COND
    return MatrixResult(
        verdict=Verdict.COND,
        reason_id="",
        reason=f"tool class '{tool_class}' conditional for role '{role}'",
        conditional_checks=cond_checks,
    )
