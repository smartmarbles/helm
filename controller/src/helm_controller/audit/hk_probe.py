"""HK-001..HK-003 PROBE automation hook entry points (spec015 Task 9.4).

HK-001: CHK-001..CHK-014 pre-send gate evaluation for one turn snapshot.
HK-002: FSM transition legality check across a snapshot stream.
HK-003: INV-001..INV-021 invariant evaluation for a snapshot stream.

All entry points:
- Accept raw dict inputs (not typed dataclass instances).
- Return structured dicts — no unhandled exceptions; all error paths return
  a dict with an ``"error"`` key instead of raising.
- Reuse the real Phase 4-8 evaluator functions; no decision logic is
  reimplemented here.
"""

from __future__ import annotations

from typing import Any

from helm_controller.contracts.blackboard import BlackboardRow
from helm_controller.contracts.snapshot import Snapshot
from helm_controller.fsm.evaluator import evaluate as evaluate_transition
from helm_controller.fsm.events import Event
from helm_controller.fsm.states import State
from helm_controller.gates.presend_checks import run_presend_checks
from helm_controller.invariants.inv_evaluator import evaluate_invariants
from helm_controller.policy.registry import AgentRoleRegistry

_REGISTRY = AgentRoleRegistry()


def hk_001(turn_snapshot: dict[str, Any]) -> dict[str, Any]:
    """HK-001: Run CHK-001..CHK-014 pre-send gate for one turn snapshot.

    Input:  ``turn_snapshot`` — dict conforming to the runtime-snapshot schema.
    Output: ``{"pass": bool, "failed_check": str|null, "state_after": str|null}``
    """
    try:
        snap = Snapshot.from_dict(turn_snapshot)
    except (KeyError, TypeError, ValueError) as exc:
        return {"pass": False, "failed_check": None, "state_after": None, "error": str(exc)}

    result = run_presend_checks(snap)
    return {
        "pass": result.passed,
        "failed_check": result.failed_check,
        "state_after": result.decision.state_after if result.decision else None,
    }


def hk_002(snapshot_stream: list[dict[str, Any]]) -> dict[str, Any]:
    """HK-002: FSM transition legality check across a snapshot stream.

    Input:  ``snapshot_stream`` — list of turn-snapshot dicts.
    Output: ``{"pass": bool, "invalid_transition_id": str|null}``
    """
    if not isinstance(snapshot_stream, list):
        return {
            "pass": False,
            "invalid_transition_id": None,
            "error": "snapshot_stream must be a list",
        }

    for i, turn in enumerate(snapshot_stream):
        try:
            snap = Snapshot.from_dict(turn)
            state_before = State(snap.state_before)
            event = Event(snap.event)
        except (KeyError, TypeError, ValueError) as exc:
            return {
                "pass": False,
                "invalid_transition_id": None,
                "error": f"turn {i}: {exc}",
            }

        result = evaluate_transition(state_before, event, snap)
        if not result.legal:
            return {
                "pass": False,
                "invalid_transition_id": result.transition_id,
                "state_before": snap.state_before,
                "event": snap.event,
            }

    return {"pass": True, "invalid_transition_id": None}


def hk_003(snapshot_stream: list[dict[str, Any]]) -> dict[str, Any]:
    """HK-003: INV-001..INV-021 invariant evaluation across a snapshot stream.

    Each stream entry may be either a plain snapshot dict OR a dict with
    ``"snapshot"`` and optional ``"blackboard"`` keys.  Entries without a
    blackboard are skipped (invariants INV-018..INV-021 need the blackboard).

    Input:  ``snapshot_stream`` — list of snapshot or ``{snapshot, blackboard}`` dicts.
    Output: ``{"pass": bool, "violated_invariants": [...]}``
    """
    if not isinstance(snapshot_stream, list):
        return {
            "pass": False,
            "violated_invariants": [],
            "error": "snapshot_stream must be a list",
        }

    all_violations: list[dict[str, Any]] = []

    for i, entry in enumerate(snapshot_stream):
        try:
            if isinstance(entry, dict) and "snapshot" in entry:
                snap_data = entry["snapshot"]
                bb_data = entry.get("blackboard")
            else:
                snap_data = entry
                bb_data = None

            snap = Snapshot.from_dict(snap_data)
            bb = BlackboardRow.from_dict(bb_data) if bb_data is not None else None
        except (KeyError, TypeError, ValueError) as exc:
            return {
                "pass": False,
                "violated_invariants": [],
                "error": f"entry {i}: {exc}",
            }

        if bb is None:
            continue

        inv = evaluate_invariants(snap, bb, _REGISTRY.resolve_role)
        for v in inv.violations:
            all_violations.append(
                {"turn": i, "invariant_id": v.invariant_id, "reason": v.reason}
            )

    return {"pass": len(all_violations) == 0, "violated_invariants": all_violations}
