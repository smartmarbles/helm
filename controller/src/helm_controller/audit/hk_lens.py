"""HK-004..HK-008 LENS automation hook entry points (spec015 Task 9.4).

HK-004: Classify a user message to EV-### (event classification, heuristic).
HK-005: Tag an agent message with outbound_sender + outbound_message_type.
HK-006: Delegation-claim vs runSubagent parity check (INV-002 enforcement).
HK-007: Open-question and approval ordering for spec/plan checkpoint traces.
HK-008: Replay a single TC fixture vector and assert expected verdict.

All entry points:
- Accept raw dict/str inputs.
- Return structured dicts — no unhandled exceptions on any input.
- HK-008 imports replay_tc from audit.replay (source module, not the test
  harness) so hk_lens.py stays in the source tree.
"""

from __future__ import annotations

from typing import Any

from helm_controller.audit.replay import replay_tc


# ---------------------------------------------------------------------------
# HK-004 — event classification (heuristic keyword matching)
# ---------------------------------------------------------------------------

_EVENT_PATTERNS: tuple[tuple[tuple[str, ...], str, float], ...] = (
    (("stop", "halt", "cancel"), "EV-002", 0.9),
    (("process audit", "what's happening", "meta question", "explain", "audit"), "EV-003", 0.8),
    (("quiz me", "quiz"), "EV-011", 0.9),
    (("inline", "answer inline"), "EV-012", 0.9),
    (("defer", "skip questions"), "EV-013", 0.8),
    (("approve", "approved", "looks good", "lgtm"), "EV-015", 0.8),
    (("revise", "revision", "update this", "feedback"), "EV-016", 0.7),
    (("reject", "rejected", "no go", "start over"), "EV-017", 0.8),
)


def hk_004(user_message: str) -> dict[str, Any]:
    """HK-004: Classify user message to EV-### via heuristic keyword matching.

    Input:  ``user_message`` — raw user turn string.
    Output: ``{"event_label": "EV-###", "confidence": float}``
    """
    if not isinstance(user_message, str):
        return {
            "event_label": None,
            "confidence": 0.0,
            "error": "user_message must be a string",
        }

    lower = user_message.lower()
    for keywords, event_label, confidence in _EVENT_PATTERNS:
        if any(kw in lower for kw in keywords):
            return {"event_label": event_label, "confidence": confidence}

    return {"event_label": "EV-001", "confidence": 0.5}


# ---------------------------------------------------------------------------
# HK-005 — outbound message ownership tagging (heuristic)
# ---------------------------------------------------------------------------


def hk_005(agent_message: str) -> dict[str, Any]:
    """HK-005: Tag outbound_sender + outbound_message_type for an agent message.

    Input:  ``agent_message`` — raw agent turn string.
    Output: ``{"outbound_sender": str, "outbound_message_type": str}``
    """
    if not isinstance(agent_message, str):
        return {
            "outbound_sender": None,
            "outbound_message_type": None,
            "error": "agent_message must be a string",
        }

    lower = agent_message.lower()

    if "approve" in lower or "reject" in lower or "revise" in lower:
        return {
            "outbound_sender": "orchestrator",
            "outbound_message_type": "approval_prompt",
        }

    if "dispatch" in lower or "delegat" in lower:
        return {
            "outbound_sender": "orchestrator",
            "outbound_message_type": "dispatch_notice",
        }

    if "?" in agent_message:
        return {
            "outbound_sender": "orchestrator",
            "outbound_message_type": "question_prompt",
        }

    if "```" in agent_message:
        return {
            "outbound_sender": "orchestrator",
            "outbound_message_type": "deliverable_content",
        }

    return {"outbound_sender": "orchestrator", "outbound_message_type": "status"}


# ---------------------------------------------------------------------------
# HK-006 — delegation-claim vs runSubagent parity
# ---------------------------------------------------------------------------


def hk_006(turn_bundle: dict[str, Any]) -> dict[str, Any]:
    """HK-006: Check delegation_claimed == false OR runSubagent >= 1 (INV-002).

    Input:  ``turn_bundle`` — dict with ``delegation_claimed`` (bool) and
            ``tool_calls.runSubagent`` (int).
    Output: ``{"pass": bool, "delegation_gap": str|null}``
    """
    if not isinstance(turn_bundle, dict):
        return {"pass": False, "delegation_gap": "turn_bundle must be a dict"}

    try:
        delegation_claimed = turn_bundle["delegation_claimed"]
        run_subagent = turn_bundle.get("tool_calls", {}).get("runSubagent", 0)
    except (KeyError, AttributeError, TypeError) as exc:
        return {"pass": False, "delegation_gap": f"malformed input: {exc}"}

    if delegation_claimed and run_subagent < 1:
        return {
            "pass": False,
            "delegation_gap": f"delegation claimed but runSubagent={run_subagent}",
        }

    return {"pass": True, "delegation_gap": None}


# ---------------------------------------------------------------------------
# HK-007 — checkpoint ordering (open-question before approval)
# ---------------------------------------------------------------------------


def hk_007(checkpoint_trace: list[dict[str, Any]]) -> dict[str, Any]:
    """HK-007: Verify open-question prompt precedes approval prompt for gate docs.

    Input:  ``checkpoint_trace`` — ordered list of checkpoint event dicts.
            Each dict: ``{"type": str, "doc_type": str, ...}``.
    Output: ``{"pass": bool, "ordering_violation": str|null}``
    """
    if not isinstance(checkpoint_trace, list):
        return {
            "pass": False,
            "ordering_violation": "checkpoint_trace must be a list",
        }

    oq_seen: dict[str, int] = {}  # doc_type -> first index of open_question_prompt

    for i, event in enumerate(checkpoint_trace):
        if not isinstance(event, dict):
            return {
                "pass": False,
                "ordering_violation": f"entry {i} is not a dict",
            }
        etype = event.get("type", "")
        doc_type = event.get("doc_type", "")

        if etype == "open_question_prompt":
            oq_seen.setdefault(doc_type, i)
        elif etype == "approval_prompt" and doc_type in {"spec", "plan"}:
            if doc_type not in oq_seen:
                return {
                    "pass": False,
                    "ordering_violation": (
                        f"approval_prompt for {doc_type} before open_question_prompt"
                    ),
                }

    return {"pass": True, "ordering_violation": None}


# ---------------------------------------------------------------------------
# HK-008 — TC fixture replay
# ---------------------------------------------------------------------------


def hk_008(tc_vector: dict[str, Any]) -> dict[str, Any]:
    """HK-008: Replay one TC fixture vector and assert expected verdict.

    Input:  ``tc_vector`` — a single TC fixture dict (see audit.replay for
            the fixture schema).
    Output: ``{"pass": bool, "tc_id": str, "verdict": str,
               "expected_verdict": str, "failed_check": str|null,
               "reason": str|null}``
    """
    try:
        result = replay_tc(tc_vector)
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        return {
            "pass": False,
            "tc_id": tc_vector.get("tc_id", "?") if isinstance(tc_vector, dict) else "?",
            "verdict": "ERROR",
            "expected_verdict": "?",
            "failed_check": None,
            "reason": str(exc),
            "error": str(exc),
        }

    return {
        "pass": result.matched,
        "tc_id": result.tc_id,
        "verdict": result.verdict,
        "expected_verdict": result.expected_verdict,
        "failed_check": result.failed_check,
        "reason": result.mismatch_reason,
    }
