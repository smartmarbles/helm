"""Unit tests for audit.hk_lens (HK-004..HK-008)."""

from __future__ import annotations

from typing import Any

import pytest

from helm_controller.audit.hk_lens import hk_004, hk_005, hk_006, hk_007, hk_008
from helm_controller.audit.replay import BASE_BLACKBOARD, BASE_SNAPSHOT, _deep_merge


# ---------------------------------------------------------------------------
# HK-004 — event classification
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message,expected_event",
    [
        ("please stop", "EV-002"),
        ("halt operations", "EV-002"),
        ("process audit now", "EV-003"),
        ("quiz me on this", "EV-011"),
        ("answer inline please", "EV-012"),
        ("defer the questions", "EV-013"),
        ("looks good, approved", "EV-015"),
        ("revise the document", "EV-016"),
        ("rejected, start over", "EV-017"),
        ("hello, carry on", "EV-001"),
    ],
)
def test_hk_004_classification(message: str, expected_event: str) -> None:
    result = hk_004(message)
    assert result["event_label"] == expected_event
    assert isinstance(result["confidence"], float)


def test_hk_004_bad_input() -> None:
    result = hk_004(123)  # type: ignore[arg-type]
    assert "error" in result
    assert result["event_label"] is None


# ---------------------------------------------------------------------------
# HK-005 — outbound message tagging
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message,expected_type",
    [
        ("please approve this", "approval_prompt"),
        ("I am going to dispatch FORGE now", "dispatch_notice"),
        ("What does this mean?", "question_prompt"),
        ("```python\nprint('done')\n```", "deliverable_content"),
        ("Work is in progress", "status"),
    ],
)
def test_hk_005_tagging(message: str, expected_type: str) -> None:
    result = hk_005(message)
    assert result["outbound_message_type"] == expected_type
    assert result["outbound_sender"] == "orchestrator"


def test_hk_005_bad_input() -> None:
    result = hk_005(42)  # type: ignore[arg-type]
    assert "error" in result
    assert result["outbound_sender"] is None


# ---------------------------------------------------------------------------
# HK-006 — delegation parity
# ---------------------------------------------------------------------------


def test_hk_006_not_claimed() -> None:
    result = hk_006({"delegation_claimed": False, "tool_calls": {"runSubagent": 0}})
    assert result["pass"] is True
    assert result["delegation_gap"] is None


def test_hk_006_claimed_with_subagent() -> None:
    result = hk_006({"delegation_claimed": True, "tool_calls": {"runSubagent": 1}})
    assert result["pass"] is True
    assert result["delegation_gap"] is None


def test_hk_006_claimed_no_subagent() -> None:
    result = hk_006({"delegation_claimed": True, "tool_calls": {"runSubagent": 0}})
    assert result["pass"] is False
    assert result["delegation_gap"] is not None


def test_hk_006_bad_input() -> None:
    result = hk_006("not_a_dict")  # type: ignore[arg-type]
    assert result["pass"] is False
    assert "delegation_gap" in result


def test_hk_006_missing_delegation_key() -> None:
    # dict input that is missing "delegation_claimed" raises KeyError inside the
    # try block, exercising the malformed-input except branch.
    result = hk_006({"tool_calls": {"runSubagent": 0}})
    assert result["pass"] is False
    assert result["delegation_gap"].startswith("malformed input:")


# ---------------------------------------------------------------------------
# HK-007 — checkpoint ordering
# ---------------------------------------------------------------------------


def test_hk_007_empty_trace() -> None:
    result = hk_007([])
    assert result["pass"] is True
    assert result["ordering_violation"] is None


def test_hk_007_correct_order() -> None:
    trace = [
        {"type": "open_question_prompt", "doc_type": "spec"},
        {"type": "approval_prompt", "doc_type": "spec"},
    ]
    result = hk_007(trace)
    assert result["pass"] is True


def test_hk_007_approval_before_oq() -> None:
    trace = [{"type": "approval_prompt", "doc_type": "spec"}]
    result = hk_007(trace)
    assert result["pass"] is False
    assert "approval_prompt for spec before open_question_prompt" in result["ordering_violation"]


def test_hk_007_non_gate_doc_no_check() -> None:
    trace = [{"type": "approval_prompt", "doc_type": "non_gate"}]
    result = hk_007(trace)
    assert result["pass"] is True


def test_hk_007_not_list() -> None:
    result = hk_007("not_a_list")  # type: ignore[arg-type]
    assert result["pass"] is False
    assert "ordering_violation" in result


def test_hk_007_bad_entry() -> None:
    result = hk_007([123])
    assert result["pass"] is False
    assert "ordering_violation" in result


# ---------------------------------------------------------------------------
# HK-008 — TC replay
# ---------------------------------------------------------------------------


def _build_tc_vector(
    snap_overrides: dict | None = None,
    bb_overrides: dict | None = None,
    expected_verdict: str = "PASS",
    expected_failed_check: str | None = None,
) -> dict:
    return {
        "tc_id": "TEST-HK008",
        "turns": [
            {
                "snapshot_overrides": snap_overrides or {},
                "blackboard_overrides": bb_overrides if bb_overrides is not None else {},
            }
        ],
        "expected_verdict": expected_verdict,
        "expected_failed_check": expected_failed_check,
    }


def test_hk_008_pass() -> None:
    tc = _build_tc_vector(expected_verdict="PASS")
    result = hk_008(tc)
    assert result["pass"] is True
    assert result["tc_id"] == "TEST-HK008"
    assert result["verdict"] == "PASS"


def test_hk_008_fail_known_bad() -> None:
    tc = _build_tc_vector(
        snap_overrides={"outbound_message_type": "deliverable_content"},
        expected_verdict="FAIL",
        expected_failed_check="INV-001",
    )
    result = hk_008(tc)
    assert result["pass"] is True
    assert result["verdict"] == "FAIL"
    assert result["failed_check"] == "INV-001"


def test_hk_008_mismatch_verdict() -> None:
    tc = _build_tc_vector(
        snap_overrides={"outbound_message_type": "deliverable_content"},
        expected_verdict="PASS",
    )
    result = hk_008(tc)
    assert result["pass"] is False


def test_hk_008_exception_bad_input() -> None:
    result = hk_008("not_a_dict")  # type: ignore[arg-type]
    assert result["pass"] is False
    assert "error" in result
    assert result["tc_id"] == "?"
