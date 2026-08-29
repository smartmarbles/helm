"""Tests for helm_controller.policy.matrix (spec015 Task 4.4).

Covers: ALLOW / DENY / COND outcomes for representative role × class
combinations, PC-001 reason ID emission (DENY outcomes), conditional_checks
tuple content on COND outcomes, UNKNOWN role, UNKNOWN class.
"""

from __future__ import annotations

import pytest

from helm_controller.policy.matrix import (
    PC_001,
    UNKNOWN_CLASS,
    UNKNOWN_ROLE,
    MatrixResult,
    Verdict,
    evaluate,
)


# ---------------------------------------------------------------------------
# ALLOW outcomes
# ---------------------------------------------------------------------------


def test_allow_read_for_orchestrator() -> None:
    result = evaluate("orchestrator", "read")
    assert result.verdict == Verdict.ALLOW
    assert result.reason_id == ""
    assert result.conditional_checks == ()


def test_allow_read_for_all_roles() -> None:
    roles = [
        "orchestrator", "clarifier", "planner", "researcher",
        "writer", "recruiter", "tester", "auditor", "implementer", "reviewer",
    ]
    for role in roles:
        result = evaluate(role, "read")
        assert result.verdict == Verdict.ALLOW, f"Expected ALLOW for {role}.read"


def test_allow_web_external_for_researcher() -> None:
    result = evaluate("researcher", "web_external")
    assert result.verdict == Verdict.ALLOW


def test_allow_execution_for_writer() -> None:
    result = evaluate("writer", "execution")
    assert result.verdict == Verdict.ALLOW


def test_allow_execution_for_tester() -> None:
    result = evaluate("tester", "execution")
    assert result.verdict == Verdict.ALLOW


def test_allow_execution_for_implementer() -> None:
    result = evaluate("implementer", "execution")
    assert result.verdict == Verdict.ALLOW


def test_allow_vscode_system_for_orchestrator() -> None:
    result = evaluate("orchestrator", "vscode_system")
    assert result.verdict == Verdict.ALLOW


def test_allow_workflow_state_for_orchestrator() -> None:
    result = evaluate("orchestrator", "workflow_state")
    assert result.verdict == Verdict.ALLOW


def test_allow_read_for_unknown_role() -> None:
    result = evaluate(UNKNOWN_ROLE, "read")
    assert result.verdict == Verdict.ALLOW


# ---------------------------------------------------------------------------
# DENY outcomes and PC-001
# ---------------------------------------------------------------------------


def test_deny_file_mutation_for_orchestrator_emits_pc001() -> None:
    result = evaluate("orchestrator", "file_mutation")
    assert result.verdict == Verdict.DENY
    assert result.reason_id == PC_001


def test_deny_file_mutation_for_researcher() -> None:
    result = evaluate("researcher", "file_mutation")
    assert result.verdict == Verdict.DENY
    assert result.reason_id == PC_001


def test_deny_agent_dispatch_for_writer() -> None:
    result = evaluate("writer", "agent_dispatch")
    assert result.verdict == Verdict.DENY
    assert result.reason_id == PC_001


def test_deny_agent_dispatch_for_researcher() -> None:
    result = evaluate("researcher", "agent_dispatch")
    assert result.verdict == Verdict.DENY
    assert result.reason_id == PC_001


def test_deny_execution_for_orchestrator_emits_pc001() -> None:
    result = evaluate("orchestrator", "execution")
    assert result.verdict == Verdict.DENY
    assert result.reason_id == PC_001


def test_deny_web_external_for_implementer() -> None:
    result = evaluate("implementer", "web_external")
    assert result.verdict == Verdict.DENY


def test_deny_workflow_state_for_implementer() -> None:
    result = evaluate("implementer", "workflow_state")
    assert result.verdict == Verdict.DENY


def test_deny_vscode_system_for_implementer() -> None:
    result = evaluate("implementer", "vscode_system")
    assert result.verdict == Verdict.DENY


def test_deny_all_non_read_for_unknown_role() -> None:
    for tool_class in [
        "agent_dispatch", "web_external", "file_mutation",
        "execution", "vscode_system", "workflow_state",
    ]:
        result = evaluate(UNKNOWN_ROLE, tool_class)
        assert result.verdict == Verdict.DENY, (
            f"Expected DENY for UNKNOWN.{tool_class}"
        )
        assert result.reason_id == PC_001


def test_deny_unknown_tool_class_emits_pc001() -> None:
    result = evaluate("orchestrator", "nonexistent_class")
    assert result.verdict == Verdict.DENY
    assert result.reason_id == PC_001
    assert "unknown tool class" in result.reason


def test_deny_unknown_tool_class_for_unknown_role() -> None:
    result = evaluate(UNKNOWN_ROLE, "nonexistent_class")
    assert result.verdict == Verdict.DENY
    assert result.reason_id == PC_001


# ---------------------------------------------------------------------------
# Unknown role fallback
# ---------------------------------------------------------------------------


def test_completely_unknown_role_falls_back_to_unknown_row() -> None:
    result = evaluate("COMPLETELY_UNKNOWN_ROLE_XYZ", "execution")
    assert result.verdict == Verdict.DENY
    assert result.reason_id == PC_001


def test_completely_unknown_role_read_is_allowed() -> None:
    result = evaluate("COMPLETELY_UNKNOWN_ROLE_XYZ", "read")
    assert result.verdict == Verdict.ALLOW


# ---------------------------------------------------------------------------
# COND outcomes
# ---------------------------------------------------------------------------


def test_cond_agent_dispatch_for_orchestrator() -> None:
    result = evaluate("orchestrator", "agent_dispatch")
    assert result.verdict == Verdict.COND
    assert "subagent_target_check" in result.conditional_checks


def test_cond_agent_dispatch_for_planner_has_subagent_check() -> None:
    result = evaluate("planner", "agent_dispatch")
    assert result.verdict == Verdict.COND
    assert "subagent_target_check" in result.conditional_checks


def test_cond_agent_dispatch_for_recruiter() -> None:
    result = evaluate("recruiter", "agent_dispatch")
    assert result.verdict == Verdict.COND
    assert "subagent_target_check" in result.conditional_checks


def test_cond_agent_dispatch_for_tester() -> None:
    result = evaluate("tester", "agent_dispatch")
    assert result.verdict == Verdict.COND
    assert "subagent_target_check" in result.conditional_checks


def test_cond_file_mutation_for_planner_has_scr_check() -> None:
    result = evaluate("planner", "file_mutation")
    assert result.verdict == Verdict.COND
    assert "scr_path_check" in result.conditional_checks


def test_cond_file_mutation_for_writer_has_scr_check() -> None:
    result = evaluate("writer", "file_mutation")
    assert result.verdict == Verdict.COND
    assert "scr_path_check" in result.conditional_checks


def test_cond_file_mutation_for_implementer_has_scr_check() -> None:
    result = evaluate("implementer", "file_mutation")
    assert result.verdict == Verdict.COND
    assert "scr_path_check" in result.conditional_checks


def test_cond_file_mutation_for_clarifier_has_scoped_and_scr() -> None:
    result = evaluate("clarifier", "file_mutation")
    assert result.verdict == Verdict.COND
    assert "scoped_path_check" in result.conditional_checks
    assert "scr_path_check" in result.conditional_checks


def test_cond_file_mutation_for_auditor_has_scoped_and_scr() -> None:
    result = evaluate("auditor", "file_mutation")
    assert result.verdict == Verdict.COND
    assert "scoped_path_check" in result.conditional_checks
    assert "scr_path_check" in result.conditional_checks


def test_cond_file_mutation_for_reviewer_has_scoped_and_scr() -> None:
    result = evaluate("reviewer", "file_mutation")
    assert result.verdict == Verdict.COND
    assert "scoped_path_check" in result.conditional_checks
    assert "scr_path_check" in result.conditional_checks


# ---------------------------------------------------------------------------
# MatrixResult dataclass
# ---------------------------------------------------------------------------


def test_matrix_result_is_frozen() -> None:
    result = MatrixResult(verdict=Verdict.ALLOW, reason_id="", reason="ok")
    with pytest.raises((AttributeError, TypeError)):
        result.verdict = Verdict.DENY  # type: ignore[misc]


def test_matrix_result_default_empty_conditional_checks() -> None:
    result = MatrixResult(verdict=Verdict.ALLOW, reason_id="", reason="ok")
    assert result.conditional_checks == ()
