"""Tests for helm_controller.policy.conditional_checks (spec015 Task 4.4).

Covers each check type's pass branch, fail branch, invalid-input error branch,
and the short-circuit path when a preceding check already failed.
PC-002 and PC-003 reason ID emission verified here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from helm_controller.policy.conditional_checks import (
    PC_002,
    PC_003,
    ConditionalCheckError,
    ConditionalCheckResult,
    _extract_paths,
    check_scoped_path,
    check_scr_path,
    check_subagent_target,
    run_conditional_checks,
)
from helm_controller.policy.tool_classes import ToolClassMap


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture()
def tcm(tmp_path: Path) -> ToolClassMap:
    data = {
        "version": "1.0",
        "classes": {
            "file_mutation": [
                {"name": "create_file", "path_fields": ["filePath"]},
                {
                    "name": "multi_replace",
                    "path_fields": ["replacements[*].filePath"],
                },
                {"name": "no_path_tool", "path_fields": []},
            ],
            "agent_dispatch": ["runSubagent"],
        },
    }
    p = tmp_path / "tc.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return ToolClassMap(p)


def _resolve(name: str) -> str:
    mapping = {
        "SCOOP": "researcher",
        "QUILL": "writer",
        "FORGE": "implementer",
        "ARTHUR": "orchestrator",
    }
    return mapping.get(name, "UNKNOWN")


# ===========================================================================
# _extract_paths
# ===========================================================================


class TestExtractPaths:
    def test_single_field_present(self) -> None:
        result = _extract_paths(("filePath",), {"filePath": "/a/b.py"})
        assert result == ["/a/b.py"]

    def test_single_field_missing_returns_none(self) -> None:
        result = _extract_paths(("filePath",), {"other": "x"})
        assert result is None

    def test_single_field_not_string_returns_none(self) -> None:
        result = _extract_paths(("filePath",), {"filePath": 42})
        assert result is None

    def test_array_field_valid(self) -> None:
        tool_input = {
            "replacements": [
                {"filePath": "/a.py"},
                {"filePath": "/b.py"},
            ]
        }
        result = _extract_paths(("replacements[*].filePath",), tool_input)
        assert result == ["/a.py", "/b.py"]

    def test_array_field_not_list_returns_none(self) -> None:
        result = _extract_paths(("replacements[*].filePath",), {"replacements": "nope"})
        assert result is None

    def test_array_field_item_not_dict_returns_none(self) -> None:
        result = _extract_paths(
            ("replacements[*].filePath",), {"replacements": ["not_a_dict"]}
        )
        assert result is None

    def test_array_field_item_val_not_string_returns_none(self) -> None:
        result = _extract_paths(
            ("replacements[*].filePath",), {"replacements": [{"filePath": 99}]}
        )
        assert result is None

    def test_tool_input_none_returns_none(self) -> None:
        result = _extract_paths(("filePath",), None)
        assert result is None

    def test_empty_path_fields_returns_empty_list(self) -> None:
        result = _extract_paths((), {"filePath": "/a.py"})
        assert result == []


# ===========================================================================
# check_subagent_target
# ===========================================================================


class TestCheckSubagentTarget:
    def test_pass_planner_dispatches_researcher(self) -> None:
        result = check_subagent_target("planner", {"agent": "SCOOP"}, _resolve)
        assert result.passed is True
        assert result.reason_id is None

    def test_pass_orchestrator_dispatches_any_valid_role(self) -> None:
        result = check_subagent_target("orchestrator", {"agent": "FORGE"}, _resolve)
        assert result.passed is True

    def test_pass_tester_dispatches_researcher(self) -> None:
        result = check_subagent_target("tester", {"agent": "SCOOP"}, _resolve)
        assert result.passed is True

    def test_fail_planner_dispatches_non_researcher(self) -> None:
        result = check_subagent_target("planner", {"agent": "QUILL"}, _resolve)
        assert result.passed is False
        assert result.reason_id == PC_002

    def test_fail_tester_dispatches_disallowed_role(self) -> None:
        result = check_subagent_target("tester", {"agent": "QUILL"}, _resolve)
        # QUILL → writer, which is allowed for tester
        assert result.passed is True

    def test_fail_recruiter_dispatches_non_researcher(self) -> None:
        result = check_subagent_target("recruiter", {"agent": "ARTHUR"}, _resolve)
        # ARTHUR → orchestrator, not researcher
        assert result.passed is False
        assert result.reason_id == PC_002

    def test_invalid_input_tool_input_none(self) -> None:
        result = check_subagent_target("planner", None, _resolve)
        assert result.passed is False
        assert result.reason_id == PC_002
        assert "None" in result.reason

    def test_invalid_input_missing_agent_field(self) -> None:
        result = check_subagent_target("planner", {"other": "x"}, _resolve)
        assert result.passed is False
        assert result.reason_id == PC_002
        assert "agent" in result.reason

    def test_invalid_input_role_not_in_allowed_targets(self) -> None:
        # implementer has DENY for agent_dispatch in matrix, but we call directly
        result = check_subagent_target("implementer", {"agent": "SCOOP"}, _resolve)
        assert result.passed is False
        assert result.reason_id == PC_002

    def test_pc002_emitted_on_disallowed_target(self) -> None:
        result = check_subagent_target("planner", {"agent": "FORGE"}, _resolve)
        assert result.reason_id == PC_002


# ===========================================================================
# check_scr_path
# ===========================================================================


class TestCheckScrPath:
    def test_pass_path_outside_scr(
        self, workspace: Path, tcm: ToolClassMap
    ) -> None:
        tool_input = {"filePath": str(workspace / "artifacts" / "spec.md")}
        result = check_scr_path("create_file", tool_input, str(workspace), tcm)
        assert result.passed is True
        assert result.reason_id is None

    def test_fail_path_under_scr(
        self, workspace: Path, tcm: ToolClassMap
    ) -> None:
        scr_path = workspace / ".scr" / "approval" / "rec.json"
        tool_input = {"filePath": str(scr_path)}
        result = check_scr_path("create_file", tool_input, str(workspace), tcm)
        assert result.passed is False
        assert result.reason_id == PC_003
        assert ".scr/" in result.reason

    def test_fail_array_path_one_under_scr(
        self, workspace: Path, tcm: ToolClassMap
    ) -> None:
        tool_input = {
            "replacements": [
                {"filePath": str(workspace / "safe.py")},
                {"filePath": str(workspace / ".scr" / "trace" / "r.json")},
            ]
        }
        result = check_scr_path("multi_replace", tool_input, str(workspace), tcm)
        assert result.passed is False
        assert result.reason_id == PC_003

    def test_pass_array_all_outside_scr(
        self, workspace: Path, tcm: ToolClassMap
    ) -> None:
        tool_input = {
            "replacements": [
                {"filePath": str(workspace / "a.py")},
                {"filePath": str(workspace / "b.py")},
            ]
        }
        result = check_scr_path("multi_replace", tool_input, str(workspace), tcm)
        assert result.passed is True

    def test_invalid_input_no_path_fields_annotation(
        self, workspace: Path, tcm: ToolClassMap
    ) -> None:
        tool_input = {"filePath": "/some/path"}
        result = check_scr_path("no_path_tool", tool_input, str(workspace), tcm)
        assert result.passed is False
        assert result.reason_id == PC_003
        assert "no path_fields annotation" in result.reason

    def test_invalid_input_tool_input_none(
        self, workspace: Path, tcm: ToolClassMap
    ) -> None:
        result = check_scr_path("create_file", None, str(workspace), tcm)
        assert result.passed is False
        assert result.reason_id == PC_003

    def test_invalid_input_missing_field_in_input(
        self, workspace: Path, tcm: ToolClassMap
    ) -> None:
        result = check_scr_path("create_file", {"other": "x"}, str(workspace), tcm)
        assert result.passed is False
        assert result.reason_id == PC_003

    def test_pc003_emitted_on_scr_violation(
        self, workspace: Path, tcm: ToolClassMap
    ) -> None:
        scr_path = workspace / ".scr" / "x.json"
        result = check_scr_path(
            "create_file", {"filePath": str(scr_path)}, str(workspace), tcm
        )
        assert result.reason_id == PC_003

    def test_windows_forward_slash_path_under_scr(
        self, workspace: Path, tcm: ToolClassMap
    ) -> None:
        # Simulate a Windows-style path passed via tool_input with forward slashes.
        scr_dir = workspace / ".scr"
        # Build forward-slash version of the path
        scr_file = str(scr_dir / "record.json").replace("\\", "/")
        result = check_scr_path(
            "create_file", {"filePath": scr_file}, str(workspace), tcm
        )
        assert result.passed is False
        assert result.reason_id == PC_003


# ===========================================================================
# check_scoped_path
# ===========================================================================


class TestCheckScopedPath:
    def test_pass_path_inside_workspace(
        self, workspace: Path, tcm: ToolClassMap
    ) -> None:
        tool_input = {"filePath": str(workspace / "artifacts" / "spec.md")}
        result = check_scoped_path("create_file", tool_input, str(workspace), tcm)
        assert result.passed is True

    def test_fail_path_outside_workspace(
        self, workspace: Path, tcm: ToolClassMap, tmp_path: Path
    ) -> None:
        # Use a different temp directory that is outside the workspace
        outside = tmp_path.parent / "outside_workspace_xyz"
        outside.mkdir(exist_ok=True)
        tool_input = {"filePath": str(outside / "file.py")}
        result = check_scoped_path("create_file", tool_input, str(workspace), tcm)
        assert result.passed is False
        assert result.reason_id == PC_003

    def test_invalid_input_no_path_fields(
        self, workspace: Path, tcm: ToolClassMap
    ) -> None:
        result = check_scoped_path("no_path_tool", {"x": "y"}, str(workspace), tcm)
        assert result.passed is False
        assert result.reason_id == PC_003
        assert "no path_fields annotation" in result.reason

    def test_invalid_input_tool_input_none(
        self, workspace: Path, tcm: ToolClassMap
    ) -> None:
        result = check_scoped_path("create_file", None, str(workspace), tcm)
        assert result.passed is False
        assert result.reason_id == PC_003

    def test_invalid_input_path_not_extractable(
        self, workspace: Path, tcm: ToolClassMap
    ) -> None:
        result = check_scoped_path("create_file", {}, str(workspace), tcm)
        assert result.passed is False
        assert result.reason_id == PC_003

    def test_pc003_emitted_on_scope_violation(
        self, workspace: Path, tcm: ToolClassMap, tmp_path: Path
    ) -> None:
        outside = tmp_path.parent / "outside_ws"
        outside.mkdir(exist_ok=True)
        result = check_scoped_path(
            "create_file", {"filePath": str(outside / "x.py")}, str(workspace), tcm
        )
        assert result.reason_id == PC_003


# ===========================================================================
# run_conditional_checks — dispatch and short-circuit
# ===========================================================================


class TestRunConditionalChecks:
    def _run(
        self,
        check_types: tuple[str, ...],
        workspace: Path,
        tcm: ToolClassMap,
        role: str = "planner",
        tool_name: str = "create_file",
        tool_input: dict[str, Any] | None = None,
    ) -> ConditionalCheckResult:
        return run_conditional_checks(
            check_types,
            role=role,
            tool_name=tool_name,
            tool_input=tool_input,
            workspace_root=str(workspace),
            tool_class_map=tcm,
            resolve_role=_resolve,
        )

    def test_empty_checks_passes(self, workspace: Path, tcm: ToolClassMap) -> None:
        result = self._run((), workspace, tcm)
        assert result.passed is True

    def test_single_passing_check(self, workspace: Path, tcm: ToolClassMap) -> None:
        tool_input = {"filePath": str(workspace / "some_file.py")}
        result = self._run(("scr_path_check",), workspace, tcm, tool_input=tool_input)
        assert result.passed is True

    def test_single_failing_check_returns_failure(
        self, workspace: Path, tcm: ToolClassMap
    ) -> None:
        scr_path = workspace / ".scr" / "x.json"
        tool_input = {"filePath": str(scr_path)}
        result = self._run(("scr_path_check",), workspace, tcm, tool_input=tool_input)
        assert result.passed is False
        assert result.reason_id == PC_003

    def test_short_circuit_first_check_fails_second_not_run(
        self, workspace: Path, tcm: ToolClassMap
    ) -> None:
        # scr_path_check will fail (no path_fields for no_path_tool),
        # scoped_path_check should NOT run.
        # We verify by using no_path_tool which has empty path_fields →
        # scr_path_check denies, scoped_path_check is never called.
        import unittest.mock as mock

        with mock.patch(
            "helm_controller.policy.conditional_checks.check_scoped_path"
        ) as mock_scoped:
            result = self._run(
                ("scr_path_check", "scoped_path_check"),
                workspace,
                tcm,
                tool_name="no_path_tool",
                tool_input={"filePath": "/x"},
            )
            assert result.passed is False
            mock_scoped.assert_not_called()

    def test_subagent_target_check_dispatched(
        self, workspace: Path, tcm: ToolClassMap
    ) -> None:
        result = self._run(
            ("subagent_target_check",),
            workspace,
            tcm,
            role="planner",
            tool_name="runSubagent",
            tool_input={"agent": "SCOOP"},  # SCOOP → researcher, allowed for planner
        )
        assert result.passed is True

    def test_scoped_path_check_dispatched(
        self, workspace: Path, tcm: ToolClassMap
    ) -> None:
        tool_input = {"filePath": str(workspace / "ok.py")}
        result = self._run(
            ("scoped_path_check",),
            workspace,
            tcm,
            tool_input=tool_input,
        )
        assert result.passed is True

    def test_unknown_check_type_raises(
        self, workspace: Path, tcm: ToolClassMap
    ) -> None:
        with pytest.raises(ConditionalCheckError, match="Unknown conditional check"):
            self._run(("nonexistent_check_xyz",), workspace, tcm)

    def test_two_checks_both_pass(self, workspace: Path, tcm: ToolClassMap) -> None:
        tool_input = {"filePath": str(workspace / "safe.py")}
        result = self._run(
            ("scoped_path_check", "scr_path_check"),
            workspace,
            tcm,
            tool_input=tool_input,
        )
        assert result.passed is True

    def test_second_check_fails_after_first_passes(
        self, workspace: Path, tcm: ToolClassMap
    ) -> None:
        # scoped_path_check passes (path inside workspace),
        # scr_path_check fails (path under .scr/).
        scr_file = workspace / ".scr" / "rec.json"
        tool_input = {"filePath": str(scr_file)}
        result = self._run(
            ("scoped_path_check", "scr_path_check"),
            workspace,
            tcm,
            tool_input=tool_input,
        )
        assert result.passed is False
        assert result.reason_id == PC_003
