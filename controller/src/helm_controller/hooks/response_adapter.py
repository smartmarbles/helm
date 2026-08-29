"""Per-event response adapter — internal decision -> VS Code-native wire shape.

spec015 Task 8.2 (SECURITY-CRITICAL). The Python controller decides in the
internal ``allow``/``deny``/``ask`` vocabulary
(:class:`~helm_controller.contracts.decision.Decision`). VS Code's hook protocol
does NOT consume that vocabulary directly: each hook event family expects a
different wire shape, and the R2 wrappers echo the controller's HTTP response
body verbatim. Therefore THIS module produces the bytes VS Code actually reads.

Cardinal rule (the reason this file is security-critical): a ``PreToolUse`` deny
MUST be expressed as ``hookSpecificOutput.permissionDecision = "deny"``. Emitting
a bare top-level ``{"decision": "deny"}`` for ``PreToolUse`` is silently ignored
by VS Code and the tool call proceeds — i.e. it fails OPEN. The block family
(``PostToolUse``/``Stop``/``SubagentStop``) is the inverse: it uses a top-level
``{"decision": "block", "reason": ...}`` and a ``permissionDecision`` there has
no effect. Mapping the wrong family fails open in one direction and bricks in the
other, so the family table below is authoritative and exhaustive.

Fail-closed posture: an unrecognized or empty ``hook_event`` (or a ``None``
decision) never produces a silent pass-through. It produces a defensive,
cross-family deny that is honored whether VS Code reads the permission field or
the block field (Watch Out #15). It deliberately omits ``continue: false`` so it
cannot brick a Class A session it cannot positively identify.
"""

from __future__ import annotations

from helm_controller.contracts.decision import Decision

PERMISSION = "permission"
BLOCK = "block"
COMMON = "common"

#: hook event -> native output family. Authoritative; do not infer at runtime.
WIRE_FAMILY: dict[str, str] = {
    "PreToolUse": PERMISSION,
    "PostToolUse": BLOCK,
    "Stop": BLOCK,
    "SubagentStop": BLOCK,
    "SessionStart": COMMON,
    "SubagentStart": COMMON,
    "UserPromptSubmit": COMMON,
    "PreCompact": COMMON,
}

#: Common-family events whose "proceed" shape is {"continue": true} (not {}).
_CONTINUE_ON_ALLOW: frozenset[str] = frozenset({"PreCompact"})

_ALLOW = "allow"
_DENY = "deny"
_ASK = "ask"


def _reason_text(decision: Decision) -> str:
    if decision.reason_id:
        return f"[{decision.reason_id}] {decision.reason}"
    return decision.reason


def to_wire(hook_event: str | None, decision: Decision | None) -> dict:
    """Render *decision* into the VS Code-native shape for *hook_event*.

    Returns the dict the controller hands back as the HTTP response body (which
    the R2 wrapper echoes verbatim). Never raises on an unknown event or a
    missing decision — both resolve to a fail-closed cross-family deny.
    """
    if decision is None:
        return _fail_closed(hook_event, None)
    family = WIRE_FAMILY.get(hook_event) if isinstance(hook_event, str) else None
    if family == PERMISSION:
        return _permission_wire(hook_event, decision)
    if family == BLOCK:
        return _block_wire(hook_event, decision)
    if family == COMMON:
        return _common_wire(hook_event, decision)
    return _fail_closed(hook_event, decision)


def _permission_wire(hook_event: str, decision: Decision) -> dict:
    verdict = {_ALLOW: _ALLOW, _DENY: _DENY, _ASK: _ASK}.get(decision.decision, _DENY)
    hso: dict = {"hookEventName": hook_event, "permissionDecision": verdict}
    if decision.reason:
        hso["permissionDecisionReason"] = _reason_text(decision)
    if decision.updated_input is not None:
        hso["updatedInput"] = decision.updated_input
    if decision.additional_context is not None:
        hso["additionalContext"] = decision.additional_context
    return {"hookSpecificOutput": hso}


def _block_wire(hook_event: str, decision: Decision) -> dict:
    if decision.decision == _ALLOW:
        return {}
    wire: dict = {"decision": "block", "reason": _reason_text(decision)}
    if decision.additional_context is not None:
        wire["hookSpecificOutput"] = {
            "hookEventName": hook_event,
            "additionalContext": decision.additional_context,
        }
    if decision.continue_ is False:
        wire["continue"] = False
        wire["stopReason"] = decision.reason
    return wire


def _common_wire(hook_event: str, decision: Decision) -> dict:
    if decision.decision == _ALLOW:
        return {"continue": True} if hook_event in _CONTINUE_ON_ALLOW else {}
    if decision.continue_ is False:
        return {
            "continue": False,
            "stopReason": decision.reason,
            "systemMessage": _reason_text(decision),
        }
    return {"systemMessage": _reason_text(decision)}


def _fail_closed(hook_event: str | None, decision: Decision | None) -> dict:
    reason = (
        _reason_text(decision)
        if decision is not None
        else "fail-closed: unrecognized hook event or missing decision"
    )
    name = hook_event if isinstance(hook_event, str) and hook_event else "UNKNOWN"
    return {
        "decision": "block",
        "reason": reason,
        "hookSpecificOutput": {
            "hookEventName": name,
            "permissionDecision": _DENY,
            "permissionDecisionReason": reason,
        },
    }
