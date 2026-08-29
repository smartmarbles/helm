"""Agent-to-role registry (spec015 Task 4.1).

Resolves an agent name arriving on a hook envelope to its policy role.
Loadable from a versioned JSON data file — onboarding a new specialist
agent requires only a data-file edit, not a code change.

Unknown agents resolve to ``UNKNOWN`` and deny all non-``read`` access
per the policy matrix (see :mod:`helm_controller.policy.matrix`).

**Data-format note (deviation from plan):** The plan names
``agent_roles.yaml``; however, Python's stdlib provides no YAML parser.
This module uses ``agent_roles.json`` (parsed by stdlib ``json``) to
preserve the project's stdlib-only runtime-path constraint. This decision
and its plan reconciliation are recorded in the spec015 plan's
"Design Adjustments During Implementation" section (the JSON-not-YAML
fold-back, whose rule home is plan Tasks 1.1 / 4.1-4.3) — a corollary of
the stdlib-only constraint in ``plan-resilience-stdlib.md`` Directive 1.
"""

from __future__ import annotations

import json
from pathlib import Path

UNKNOWN_ROLE = "UNKNOWN"

_DEFAULT_DATA_FILE = Path(__file__).parent / "agent_roles.json"


class RegistryError(Exception):
    """Raised when the agent_roles data file cannot be read or parsed."""


def _load_roles(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RegistryError(f"Cannot read agent_roles data file '{path}': {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RegistryError(f"Malformed JSON in agent_roles data file '{path}': {exc}") from exc
    roles = data.get("roles")
    if not isinstance(roles, dict):
        raise RegistryError(
            f"agent_roles data file '{path}' missing top-level 'roles' dict"
        )
    return {str(k): str(v) for k, v in roles.items()}


class AgentRoleRegistry:
    """Resolves agent names to their policy role.

    Args:
        data_file: Path to the JSON data file.  Defaults to the bundled
            ``agent_roles.json`` alongside this module.
    """

    def __init__(self, data_file: Path | None = None) -> None:
        self._roles: dict[str, str] = _load_roles(data_file or _DEFAULT_DATA_FILE)

    def resolve_role(self, agent_name: str) -> str:
        """Return the policy role for *agent_name*.

        Returns ``UNKNOWN`` when the agent is not in the registry.
        """
        return self._roles.get(agent_name, UNKNOWN_ROLE)

    def known_agents(self) -> frozenset[str]:
        """Return the set of registered agent names."""
        return frozenset(self._roles)
