"""Unit tests for audit.hk_profile4 (HK-009..HK-012)."""

from __future__ import annotations

from typing import Any

from helm_controller.audit.hk_profile4 import hk_009, hk_010, hk_011, hk_012
from helm_controller.audit.replay import BASE_BLACKBOARD, BASE_SNAPSHOT, _deep_merge


def _bb(**overrides: Any) -> dict[str, Any]:
    return _deep_merge(BASE_BLACKBOARD, overrides)


def _snap(**overrides: Any) -> dict[str, Any]:
    return _deep_merge(BASE_SNAPSHOT, overrides)


# ---------------------------------------------------------------------------
# HK-009 — blackboard integrity for one turn
# ---------------------------------------------------------------------------


def test_hk_009_plain_snapshot_no_blackboard() -> None:
    result = hk_009(_snap())
    assert result["pass"] is True
    assert result["blocked_gate_id"] is None
    assert result["reason"] == "no blackboard present"


def test_hk_009_wrapped_without_blackboard_key() -> None:
    result = hk_009({"snapshot": _snap()})
    assert result["pass"] is True
    assert result["reason"] == "no blackboard present"


def test_hk_009_wrapped_pass() -> None:
    result = hk_009({"snapshot": _snap(), "blackboard": _bb()})
    assert result["pass"] is True
    assert result["blocked_gate_id"] is None
    assert result["reason"] is None


def test_hk_009_gate_failure() -> None:
    result = hk_009({"snapshot": _snap(), "blackboard": _bb(row_present=False)})
    assert result["pass"] is False
    assert result["blocked_gate_id"] == "BG-001"
    assert result["reason"] is not None


def test_hk_009_malformed_snapshot() -> None:
    result = hk_009({"snapshot": {}})
    assert result["pass"] is False
    assert result["blocked_gate_id"] is None
    assert isinstance(result["reason"], str)


# ---------------------------------------------------------------------------
# HK-010 — gate-transition checker across a snapshot stream
# ---------------------------------------------------------------------------


def test_hk_010_not_a_list() -> None:
    result = hk_010({"snapshot": _snap()})  # type: ignore[arg-type]
    assert result["pass"] is False
    assert result["gate_transition_violation"] == "snapshot_stream must be a list"


def test_hk_010_pass() -> None:
    stream = [{"snapshot": _snap(), "blackboard": _bb()}]
    result = hk_010(stream)
    assert result["pass"] is True
    assert result["gate_transition_violation"] is None


def test_hk_010_entry_without_blackboard_is_skipped() -> None:
    stream = [{"snapshot": _snap()}]
    result = hk_010(stream)
    assert result["pass"] is True
    assert result["gate_transition_violation"] is None


def test_hk_010_non_dict_entry() -> None:
    result = hk_010(["not-a-dict"])
    assert result["pass"] is False
    assert result["gate_transition_violation"].startswith("entry 0:")


def test_hk_010_gate_failure() -> None:
    stream = [{"snapshot": _snap(), "blackboard": _bb(row_present=False)}]
    result = hk_010(stream)
    assert result["pass"] is False
    assert "turn 0:" in result["gate_transition_violation"]
    assert "BG-001" in result["gate_transition_violation"]


# ---------------------------------------------------------------------------
# HK-011 — owner-lock consistency across a blackboard stream
# ---------------------------------------------------------------------------


def test_hk_011_not_a_list() -> None:
    result = hk_011(_bb())  # type: ignore[arg-type]
    assert result["pass"] is False
    assert result["contention_detail"] == "blackboard_stream must be a list"


def test_hk_011_malformed_entry() -> None:
    result = hk_011([{"row_present": True}])
    assert result["pass"] is False
    assert result["contention_detail"].startswith("entry 0:")


def test_hk_011_active_pass() -> None:
    result = hk_011([_bb()])
    assert result["pass"] is True
    assert result["workflow_id"] is None
    assert result["contention_detail"] is None


def test_hk_011_active_contention() -> None:
    row = _bb(owner_lock={"active_lock_count": 0, "active": None})
    result = hk_011([row])
    assert result["pass"] is False
    assert result["workflow_id"] == "wf-001"
    assert "active workflow" in result["contention_detail"]


def test_hk_011_terminal_pass() -> None:
    row = _bb(
        workflow_lifecycle="terminal",
        owner_lock={"active": None, "active_lock_count": 0},
    )
    result = hk_011([row])
    assert result["pass"] is True
    assert result["contention_detail"] is None


def test_hk_011_terminal_holds_lock() -> None:
    row = _bb(
        workflow_lifecycle="non_terminal_suspended",
        owner_lock={"active": "ARTHUR", "active_lock_count": 1},
    )
    result = hk_011([row])
    assert result["pass"] is False
    assert "suspended/terminal" in result["contention_detail"]


def test_hk_011_unknown_lifecycle_is_ignored() -> None:
    # A lifecycle value outside the known set hits neither the if nor the elif
    # branch and is treated as a no-op pass.
    row = _bb(workflow_lifecycle="non_terminal_unknown")
    result = hk_011([row])
    assert result["pass"] is True
    assert result["contention_detail"] is None


# ---------------------------------------------------------------------------
# HK-012 — mutation-after-terminal checker
# ---------------------------------------------------------------------------


def test_hk_012_not_a_list() -> None:
    result = hk_012({"workflow_id": "w"})  # type: ignore[arg-type]
    assert result["pass"] is False
    assert result["error"] == "terminal_row_diffs must be a list"


def test_hk_012_non_dict_entry() -> None:
    result = hk_012(["not-a-dict"])
    assert result["pass"] is False
    assert result["error"] == "entry 0 must be a dict"


def test_hk_012_terminal_mutation_violation() -> None:
    diffs = [{"workflow_id": "wf-9", "is_terminal": True, "mutated_fields": ["owner_lock.active"]}]
    result = hk_012(diffs)
    assert result["pass"] is False
    assert result["workflow_id"] == "wf-9"
    assert result["mutated_fields"] == ["owner_lock.active"]


def test_hk_012_pass() -> None:
    diffs = [
        {"workflow_id": "wf-1", "is_terminal": False, "mutated_fields": ["x"]},
        {"workflow_id": "wf-2", "is_terminal": True, "mutated_fields": []},
        {"workflow_id": "wf-3"},
    ]
    result = hk_012(diffs)
    assert result["pass"] is True
    assert result["workflow_id"] is None
    assert result["mutated_fields"] == []


def test_hk_012_empty_list() -> None:
    result = hk_012([])
    assert result["pass"] is True
