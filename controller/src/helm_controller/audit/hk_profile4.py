"""HK-009..HK-012 Profile #4 automation hook entry points (spec015 Task 9.5).

HK-009: Blackboard integrity checker — BG-001..BG-006 for one turn snapshot.
HK-010: Gate-transition checker — BG gates across a snapshot stream.
HK-011: Owner-lock checker — lock consistency across a blackboard stream.
HK-012: Mutation-after-terminal checker — BG-006 on terminal row diffs.

All entry points reuse Phase 6 gates/invariants; no gate logic is reimplemented.
All return structured dicts — no unhandled exceptions on any input.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from helm_controller.contracts.blackboard import BlackboardRow
from helm_controller.contracts.snapshot import Snapshot
from helm_controller.gates.bg_evaluator import evaluate_blackboard_gates
from helm_controller.gates.bg_rules import FAIL_REASON

_NOW = datetime(2026, 5, 31, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# HK-009 — blackboard integrity for one turn
# ---------------------------------------------------------------------------


def hk_009(turn_snapshot: dict[str, Any]) -> dict[str, Any]:
    """HK-009: BG-001..BG-006 integrity check for one turn.

    Input:  ``turn_snapshot`` — either a plain snapshot dict or
            ``{"snapshot": {...}, "blackboard": {...}}``.
    Output: ``{"pass": bool, "blocked_gate_id": str|null, "reason": str|null}``
    """
    try:
        if isinstance(turn_snapshot, dict) and "snapshot" in turn_snapshot:
            snap_data = turn_snapshot["snapshot"]
            bb_data = turn_snapshot.get("blackboard")
        else:
            snap_data = turn_snapshot
            bb_data = None

        snap = Snapshot.from_dict(snap_data)
        if bb_data is None:
            return {"pass": True, "blocked_gate_id": None, "reason": "no blackboard present"}

        bb = BlackboardRow.from_dict(bb_data)
    except (KeyError, TypeError, ValueError) as exc:
        return {"pass": False, "blocked_gate_id": None, "reason": str(exc)}

    bg = evaluate_blackboard_gates(snap, bb, now=_NOW)
    if bg.passed:
        return {"pass": True, "blocked_gate_id": None, "reason": None}

    return {
        "pass": False,
        "blocked_gate_id": bg.first_failure_id,
        "reason": FAIL_REASON.get(bg.first_failure_id or "", "unknown gate failure"),
    }


# ---------------------------------------------------------------------------
# HK-010 — gate-transition checker across a snapshot stream
# ---------------------------------------------------------------------------


def hk_010(snapshot_stream: list[dict[str, Any]]) -> dict[str, Any]:
    """HK-010: BG gate check across a snapshot stream (Profile #4).

    Each stream entry: ``{"snapshot": {...}, "blackboard": {...}}``.

    Input:  ``snapshot_stream`` — list of ``{snapshot, blackboard}`` dicts.
    Output: ``{"pass": bool, "gate_transition_violation": str|null}``
    """
    if not isinstance(snapshot_stream, list):
        return {
            "pass": False,
            "gate_transition_violation": "snapshot_stream must be a list",
        }

    for i, entry in enumerate(snapshot_stream):
        try:
            snap_data = entry.get("snapshot", entry) if isinstance(entry, dict) else entry
            bb_data = entry.get("blackboard") if isinstance(entry, dict) else None
            snap = Snapshot.from_dict(snap_data)
            if bb_data is None:
                continue
            bb = BlackboardRow.from_dict(bb_data)
        except (KeyError, TypeError, ValueError) as exc:
            return {
                "pass": False,
                "gate_transition_violation": f"entry {i}: {exc}",
            }

        bg = evaluate_blackboard_gates(snap, bb, now=_NOW)
        if not bg.passed:
            return {
                "pass": False,
                "gate_transition_violation": (
                    f"turn {i}: {bg.first_failure_id} — "
                    f"{FAIL_REASON.get(bg.first_failure_id or '', 'gate failure')}"
                ),
            }

    return {"pass": True, "gate_transition_violation": None}


# ---------------------------------------------------------------------------
# HK-011 — owner-lock consistency across a blackboard stream
# ---------------------------------------------------------------------------


def hk_011(blackboard_stream: list[dict[str, Any]]) -> dict[str, Any]:
    """HK-011: Owner-lock check across a stream of blackboard row dicts.

    Rule: active workflows hold exactly one non-stale lock; suspended and
    terminal workflows hold none (INV-021 / POL-053).

    Input:  ``blackboard_stream`` — list of blackboard-row dicts.
    Output: ``{"pass": bool, "workflow_id": str|null, "contention_detail": str|null}``
    """
    if not isinstance(blackboard_stream, list):
        return {
            "pass": False,
            "workflow_id": None,
            "contention_detail": "blackboard_stream must be a list",
        }

    for i, bb_data in enumerate(blackboard_stream):
        try:
            bb = BlackboardRow.from_dict(bb_data)
        except (KeyError, TypeError, ValueError) as exc:
            return {
                "pass": False,
                "workflow_id": None,
                "contention_detail": f"entry {i}: {exc}",
            }

        lock = bb.owner_lock
        if bb.workflow_lifecycle == "non_terminal_active":
            if lock.active_lock_count != 1 or lock.is_stale or lock.active is None:
                return {
                    "pass": False,
                    "workflow_id": bb.workflow_id,
                    "contention_detail": (
                        f"entry {i}: active workflow must hold exactly 1 non-stale lock"
                    ),
                }
        elif bb.workflow_lifecycle in {"non_terminal_suspended", "terminal"}:
            if lock.active_lock_count != 0 or lock.active is not None:
                return {
                    "pass": False,
                    "workflow_id": bb.workflow_id,
                    "contention_detail": (
                        f"entry {i}: suspended/terminal workflow must hold no locks"
                    ),
                }

    return {"pass": True, "workflow_id": None, "contention_detail": None}


# ---------------------------------------------------------------------------
# HK-012 — mutation-after-terminal checker
# ---------------------------------------------------------------------------


def hk_012(terminal_row_diffs: list[dict[str, Any]]) -> dict[str, Any]:
    """HK-012: Mutation-after-terminal check (BG-006 audit surface).

    Each diff entry: ``{"workflow_id": str, "is_terminal": bool, "mutated_fields": [...]}``.

    Input:  ``terminal_row_diffs`` — list of row-diff dicts.
    Output: ``{"pass": bool, "workflow_id": str|null, "mutated_fields": [...]}``
    """
    if not isinstance(terminal_row_diffs, list):
        return {
            "pass": False,
            "workflow_id": None,
            "mutated_fields": [],
            "error": "terminal_row_diffs must be a list",
        }

    for i, row_diff in enumerate(terminal_row_diffs):
        if not isinstance(row_diff, dict):
            return {
                "pass": False,
                "workflow_id": None,
                "mutated_fields": [],
                "error": f"entry {i} must be a dict",
            }

        workflow_id = row_diff.get("workflow_id")
        is_terminal = row_diff.get("is_terminal", False)
        mutated_fields = row_diff.get("mutated_fields", [])

        if is_terminal and mutated_fields:
            return {
                "pass": False,
                "workflow_id": workflow_id,
                "mutated_fields": list(mutated_fields),
            }

    return {"pass": True, "workflow_id": None, "mutated_fields": []}
