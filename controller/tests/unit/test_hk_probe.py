"""Unit tests for audit.hk_probe (HK-001..HK-003)."""

from __future__ import annotations

from typing import Any

import pytest

from helm_controller.audit.hk_probe import hk_001, hk_002, hk_003


# ---------------------------------------------------------------------------
# HK-001 — CHK presend gate
# ---------------------------------------------------------------------------


def test_hk_001_pass(snapshot_factory: Any) -> None:
    snap_dict = snapshot_factory().to_dict()
    result = hk_001(snap_dict)
    assert result["pass"] is True
    assert result["failed_check"] is None


def test_hk_001_fail_chk004(snapshot_factory: Any) -> None:
    snap_dict = snapshot_factory(outbound_message_type="deliverable_content").to_dict()
    result = hk_001(snap_dict)
    assert result["pass"] is False
    assert result["failed_check"] == "CHK-004"


def test_hk_001_bad_input() -> None:
    result = hk_001({"not_a_valid_snapshot": True})
    assert "error" in result
    assert result["pass"] is False


# ---------------------------------------------------------------------------
# HK-002 — FSM legality stream
# ---------------------------------------------------------------------------


def test_hk_002_pass(snapshot_factory: Any) -> None:
    stream = [snapshot_factory().to_dict()]
    result = hk_002(stream)
    assert result["pass"] is True
    assert result["invalid_transition_id"] is None


def test_hk_002_illegal(snapshot_factory: Any) -> None:
    snap_dict = snapshot_factory(
        state_before="ST-900",
        state_after="ST-900",
        event="EV-004",
    ).to_dict()
    result = hk_002([snap_dict])
    assert result["pass"] is False
    assert result.get("state_before") == "ST-900"
    assert result.get("event") == "EV-004"


def test_hk_002_not_list() -> None:
    result = hk_002("not_a_list")  # type: ignore[arg-type]
    assert result["pass"] is False
    assert "error" in result


def test_hk_002_bad_turn() -> None:
    result = hk_002([{"missing_required_fields": True}])
    assert result["pass"] is False
    assert "error" in result


# ---------------------------------------------------------------------------
# HK-003 — INV suite stream
# ---------------------------------------------------------------------------


def test_hk_003_pass(snapshot_factory: Any, blackboard_factory: Any) -> None:
    entry = {
        "snapshot": snapshot_factory().to_dict(),
        "blackboard": blackboard_factory().to_dict(),
    }
    result = hk_003([entry])
    assert result["pass"] is True
    assert result["violated_invariants"] == []


def test_hk_003_violation_inv001(snapshot_factory: Any, blackboard_factory: Any) -> None:
    snap_dict = snapshot_factory(outbound_message_type="deliverable_content").to_dict()
    entry = {"snapshot": snap_dict, "blackboard": blackboard_factory().to_dict()}
    result = hk_003([entry])
    assert result["pass"] is False
    ids = [v["invariant_id"] for v in result["violated_invariants"]]
    assert "INV-001" in ids


def test_hk_003_not_list() -> None:
    result = hk_003("not_a_list")  # type: ignore[arg-type]
    assert result["pass"] is False
    assert "error" in result


def test_hk_003_no_blackboard(snapshot_factory: Any) -> None:
    entry = {"snapshot": snapshot_factory().to_dict()}
    result = hk_003([entry])
    assert result["pass"] is True
    assert result["violated_invariants"] == []


def test_hk_003_plain_entry(snapshot_factory: Any) -> None:
    result = hk_003([snapshot_factory().to_dict()])
    assert result["pass"] is True
    assert result["violated_invariants"] == []


def test_hk_003_bad_entry(snapshot_factory: Any) -> None:
    result = hk_003([{"snapshot": "not_a_dict"}])
    assert result["pass"] is False
    assert "error" in result
