"""Direct tests for the POL-053 stage/state/role consistency map (Task 6.5).

The BG and invariant suites only traverse the consistent-triple path, so the
inconsistency branches and unknown-key fallbacks are exercised here by direct
invocation to reach full branch coverage.
"""

from __future__ import annotations

from helm_controller.gates.stage_state_map import (
    Consistency,
    allowed_states,
    check_consistency,
    registry_role,
)
from helm_controller.policy.registry import UNKNOWN_ROLE, AgentRoleRegistry


# --- allowed_states (BG-002 input) -----------------------------------------


def test_allowed_states_known_stage() -> None:
    assert allowed_states("prepare_dispatch") == frozenset({"ST-020", "ST-903"})


def test_allowed_states_unknown_stage_returns_none() -> None:
    assert allowed_states("nonexistent_stage") is None


# --- registry_role (INV-021 role lookup) -----------------------------------


def test_registry_role_known_agent_name() -> None:
    registry = AgentRoleRegistry()
    assert registry_role("ARTHUR", registry.resolve_role) == "orchestrator"


def test_registry_role_unregistered_agent_name() -> None:
    registry = AgentRoleRegistry()
    assert registry_role("NOBODY", registry.resolve_role) == UNKNOWN_ROLE


def test_registry_role_null_active_is_none() -> None:
    registry = AgentRoleRegistry()
    assert registry_role(None, registry.resolve_role) is None


# --- check_consistency (all five POL-053 branches) -------------------------


def test_check_consistency_consistent_triple() -> None:
    assert (
        check_consistency("intake", "ST-000", "orchestrator")
        is Consistency.CONSISTENT
    )


def test_check_consistency_consistent_null_owner_stage() -> None:
    assert check_consistency("suspended", "ST-000", None) is Consistency.CONSISTENT


def test_check_consistency_unknown_stage() -> None:
    assert (
        check_consistency("bogus", "ST-000", "orchestrator")
        is Consistency.UNKNOWN_STAGE
    )


def test_check_consistency_unknown_state() -> None:
    assert (
        check_consistency("intake", "ST-999", "orchestrator")
        is Consistency.UNKNOWN_STATE
    )


def test_check_consistency_inconsistent_state() -> None:
    assert (
        check_consistency("intake", "ST-010", "orchestrator")
        is Consistency.INCONSISTENT_STATE
    )


def test_check_consistency_inconsistent_role() -> None:
    assert (
        check_consistency("intake", "ST-000", "clarifier")
        is Consistency.INCONSISTENT_ROLE
    )
