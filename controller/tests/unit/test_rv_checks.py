"""Tests for residual parity checks RV-001/002/003 (spec015 Task 8.4 / 8.5).

Covers each check's trigger condition, the non-trigger guards, and
``evaluate_residual`` end-to-end including the fail-closed ``PC-008`` paths
(unavailable / malformed transcript) and the clean / empty short-circuits. A
triggered residual denies via the event-native top-level ``decision: "block"``
once routed through the Task 8.2 response adapter — never a bare ``deny``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from helm_controller.hooks.response_adapter import to_wire
from helm_controller.residual.rv_checks import (
    ORCHESTRATOR_ROLE,
    evaluate_residual,
    run_residual_checks,
)
from helm_controller.residual.transcript_reader import (
    ASSISTANT_MESSAGE,
    TOOL_CALL,
    TranscriptEvent,
)


def _msg(text: str) -> TranscriptEvent:
    return TranscriptEvent(ASSISTANT_MESSAGE, text, None, {})


def _tool(name: str | None) -> TranscriptEvent:
    return TranscriptEvent(TOOL_CALL, "", name, {})


def _write(tmp_path: Path, *objs: object) -> str:
    path = tmp_path / "t.jsonl"
    path.write_text(
        "\n".join(json.dumps(o) if not isinstance(o, str) else o for o in objs),
        encoding="utf-8",
    )
    return str(path)


# --------------------------------------------------------------------------- #
# run_residual_checks — trigger conditions
# --------------------------------------------------------------------------- #
def test_rv001_delegation_claim_without_subagent() -> None:
    finding = run_residual_checks(
        [_msg("I'll delegate to FORGE for this.")], role="implementer"
    )
    assert finding is not None
    assert finding.check_id == "RV-001"


def test_rv001_not_triggered_when_subagent_called() -> None:
    events = [_msg("I'll delegate to FORGE."), _tool("runSubagent")]
    assert run_residual_checks(events, role="implementer") is None


def test_rv002_orchestrator_deliverable_without_delegation() -> None:
    finding = run_residual_checks(
        [_msg("Here's the implementation you asked for.")], role=ORCHESTRATOR_ROLE
    )
    assert finding is not None
    assert finding.check_id == "RV-002"


def test_rv002_not_triggered_for_non_orchestrator() -> None:
    assert (
        run_residual_checks(
            [_msg("Here's the implementation.")], role="implementer"
        )
        is None
    )


def test_rv003_bypass_language_with_execution_dispatch() -> None:
    events = [_msg("I'll skip approval and run it."), _tool("run_in_terminal")]
    finding = run_residual_checks(events, role="implementer")
    assert finding is not None
    assert finding.check_id == "RV-003"


def test_rv003_not_triggered_without_execution_tool() -> None:
    assert (
        run_residual_checks([_msg("skip approval please")], role="implementer")
        is None
    )


def test_clean_transcript_has_no_finding() -> None:
    events = [_msg("Working on the task normally."), _tool("read_file")]
    assert run_residual_checks(events, role=ORCHESTRATOR_ROLE) is None


def test_tool_call_without_name_is_ignored() -> None:
    # Exercises the `and e.tool_name` guard in the tool-name set comprehension.
    events = [_msg("I'll skip approval."), _tool(None), _tool("run_task")]
    finding = run_residual_checks(events, role="implementer")
    assert finding is not None
    assert finding.check_id == "RV-003"


# --------------------------------------------------------------------------- #
# evaluate_residual — end-to-end with fail-closed paths
# --------------------------------------------------------------------------- #
def test_evaluate_no_path_fails_closed_pc008() -> None:
    decision = evaluate_residual(None, role="implementer")
    assert decision is not None
    assert decision.decision == "deny"
    assert decision.reason_id == "PC-008"


def test_evaluate_missing_file_fails_closed_pc008(tmp_path: Path) -> None:
    decision = evaluate_residual(str(tmp_path / "nope.jsonl"), role="implementer")
    assert decision is not None
    assert decision.reason_id == "PC-008"


def test_evaluate_malformed_transcript_fails_closed_pc008(tmp_path: Path) -> None:
    path = _write(tmp_path, "{broken")
    decision = evaluate_residual(path, role="implementer")
    assert decision is not None
    assert decision.reason_id == "PC-008"


def test_evaluate_empty_transcript_is_clean(tmp_path: Path) -> None:
    path = _write(tmp_path, "", "   ")
    assert evaluate_residual(path, role="implementer") is None


def test_evaluate_clean_transcript_returns_none(tmp_path: Path) -> None:
    path = _write(tmp_path, {"type": "assistant", "text": "all good"})
    assert evaluate_residual(path, role="implementer") is None


def test_evaluate_violation_returns_rv_deny_with_reroute(tmp_path: Path) -> None:
    path = _write(tmp_path, {"type": "assistant", "text": "I'll delegate to FORGE."})
    decision = evaluate_residual(path, role="implementer")
    assert decision is not None
    assert decision.decision == "deny"
    assert decision.reason_id == "RV-001"
    assert decision.additional_context is not None


# --------------------------------------------------------------------------- #
# residual deny routes through the adapter as top-level block (not bare deny)
# --------------------------------------------------------------------------- #
def test_residual_deny_routes_as_top_level_block(tmp_path: Path) -> None:
    path = _write(tmp_path, {"type": "assistant", "text": "I'll delegate to FORGE."})
    decision = evaluate_residual(path, role="implementer")
    assert decision is not None
    wire = to_wire("Stop", decision)
    assert wire["decision"] == "block"
    assert wire["hookSpecificOutput"]["additionalContext"] == decision.additional_context
    assert wire["hookSpecificOutput"]["hookEventName"] == "Stop"
    # The cardinal sin: a bare top-level permission verdict must NOT appear.
    assert "permissionDecision" not in wire


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
