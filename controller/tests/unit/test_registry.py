"""Tests for helm_controller.policy.registry (spec015 Task 4.4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from helm_controller.policy.registry import (
    UNKNOWN_ROLE,
    AgentRoleRegistry,
    RegistryError,
    _load_roles,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def valid_data_file(tmp_path: Path) -> Path:
    p = tmp_path / "agent_roles.json"
    p.write_text(
        json.dumps(
            {
                "version": "1.0",
                "roles": {
                    "ARTHUR": "orchestrator",
                    "FORGE": "implementer",
                },
            }
        ),
        encoding="utf-8",
    )
    return p


# ---------------------------------------------------------------------------
# _load_roles — happy path
# ---------------------------------------------------------------------------


def test_load_roles_returns_mapping(valid_data_file: Path) -> None:
    roles = _load_roles(valid_data_file)
    assert roles["ARTHUR"] == "orchestrator"
    assert roles["FORGE"] == "implementer"


# ---------------------------------------------------------------------------
# _load_roles — error branches
# ---------------------------------------------------------------------------


def test_load_roles_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.json"
    with pytest.raises(RegistryError, match="Cannot read"):
        _load_roles(missing)


def test_load_roles_malformed_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(RegistryError, match="Malformed JSON"):
        _load_roles(bad)


def test_load_roles_missing_roles_key(tmp_path: Path) -> None:
    p = tmp_path / "no_roles.json"
    p.write_text(json.dumps({"version": "1.0"}), encoding="utf-8")
    with pytest.raises(RegistryError, match="missing top-level 'roles' dict"):
        _load_roles(p)


def test_load_roles_roles_not_dict(tmp_path: Path) -> None:
    p = tmp_path / "roles_list.json"
    p.write_text(json.dumps({"roles": ["ARTHUR"]}), encoding="utf-8")
    with pytest.raises(RegistryError, match="missing top-level 'roles' dict"):
        _load_roles(p)


# ---------------------------------------------------------------------------
# AgentRoleRegistry — resolve_role
# ---------------------------------------------------------------------------


def test_resolve_known_agent(valid_data_file: Path) -> None:
    reg = AgentRoleRegistry(valid_data_file)
    assert reg.resolve_role("ARTHUR") == "orchestrator"
    assert reg.resolve_role("FORGE") == "implementer"


def test_resolve_unknown_agent_returns_unknown(valid_data_file: Path) -> None:
    reg = AgentRoleRegistry(valid_data_file)
    assert reg.resolve_role("NONEXISTENT") == UNKNOWN_ROLE


# ---------------------------------------------------------------------------
# AgentRoleRegistry — known_agents
# ---------------------------------------------------------------------------


def test_known_agents_returns_all_registered(valid_data_file: Path) -> None:
    reg = AgentRoleRegistry(valid_data_file)
    known = reg.known_agents()
    assert "ARTHUR" in known
    assert "FORGE" in known
    assert "NONEXISTENT" not in known


# ---------------------------------------------------------------------------
# AgentRoleRegistry — default bundled data file
# ---------------------------------------------------------------------------


def test_default_data_file_loads_all_canonical_agents() -> None:
    reg = AgentRoleRegistry()
    for agent, expected_role in [
        ("ARTHUR", "orchestrator"),
        ("QUIZ", "clarifier"),
        ("SAGE", "planner"),
        ("SCOOP", "researcher"),
        ("QUILL", "writer"),
        ("MERLIN", "recruiter"),
        ("PROBE", "tester"),
        ("LENS", "auditor"),
        ("FORGE", "implementer"),
    ]:
        assert reg.resolve_role(agent) == expected_role, (
            f"Expected {agent} → {expected_role}"
        )


def test_unknown_agent_on_default_data() -> None:
    reg = AgentRoleRegistry()
    assert reg.resolve_role("UNKNOWN_AGENT_XYZ") == UNKNOWN_ROLE
