"""Residual parity check logic for Stop / SubagentStop (spec015 Task 8.4).

Implements the three best-effort residual checks from boundary contract §7.1:

* ``RV-001`` — delegation claimed in prose but no same-turn ``runSubagent`` call.
* ``RV-002`` — an orchestrator produced deliverable content directly, without
  delegating.
* ``RV-003`` — approval-gate bypass language together with an execution dispatch
  in the same turn.

The phrase heuristics here are intentionally conservative real-time tripwires,
not a truth oracle: per §7.3, LENS plus the PROBE regression suites remain the
authoritative post-hoc layer. A triggered check denies via the event-native
top-level ``decision: "block"`` shape with a corrective ``additionalContext``
reroute; that shape is produced by the Task 8.2 response adapter from the
internal :class:`Decision` returned here.
"""

from __future__ import annotations

from dataclasses import dataclass

from helm_controller.contracts.decision import Decision
from helm_controller.residual.transcript_reader import (
    ASSISTANT_MESSAGE,
    TOOL_CALL,
    EmptyTranscriptError,
    MalformedTranscriptError,
    TranscriptEvent,
    TranscriptUnavailableError,
    read_transcript,
)

ORCHESTRATOR_ROLE = "orchestrator"
SUBAGENT_TOOL = "runSubagent"
TRANSCRIPT_UNAVAILABLE_REASON_ID = "PC-008"

EXECUTION_TOOLS: frozenset[str] = frozenset(
    {"run_in_terminal", "create_and_run_task", "run_task", "execution_subagent"}
)

_DELEGATION_CLAIMS: tuple[str, ...] = (
    "i'll delegate",
    "i will delegate",
    "i am delegating",
    "i'm delegating",
    "delegated to",
    "i'll dispatch",
    "i will dispatch",
    "dispatching to",
    "handing off to",
)

_DELIVERABLE_MARKERS: tuple[str, ...] = (
    "here's the implementation",
    "here is the implementation",
    "i've written",
    "i have written",
    "i wrote the",
    "i created the file",
    "```",
)

_BYPASS_MARKERS: tuple[str, ...] = (
    "skip approval",
    "without approval",
    "without waiting for approval",
    "bypass the approval",
    "bypass approval",
    "no need to wait for approval",
    "proceeding without approval",
)

_REROUTE = (
    "Residual parity violation detected at turn boundary. Reroute: comply with the "
    "delegation/approval protocol before completing this turn."
)


@dataclass(frozen=True)
class ResidualFinding:
    """A single residual parity violation."""

    check_id: str
    reason: str


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def run_residual_checks(
    events: list[TranscriptEvent], *, role: str
) -> ResidualFinding | None:
    """Scan *events* for the first RV-001/RV-002/RV-003 violation (in order)."""
    prose = " ".join(
        e.text for e in events if e.event_type == ASSISTANT_MESSAGE
    ).lower()
    tool_names = {
        e.tool_name for e in events if e.event_type == TOOL_CALL and e.tool_name
    }
    has_subagent = SUBAGENT_TOOL in tool_names
    has_execution = bool(tool_names & EXECUTION_TOOLS)

    if _contains_any(prose, _DELEGATION_CLAIMS) and not has_subagent:
        return ResidualFinding(
            "RV-001", "delegation claimed in prose but no runSubagent call in turn"
        )
    if (
        role == ORCHESTRATOR_ROLE
        and _contains_any(prose, _DELIVERABLE_MARKERS)
        and not has_subagent
    ):
        return ResidualFinding(
            "RV-002", "orchestrator produced deliverable content without delegation"
        )
    if _contains_any(prose, _BYPASS_MARKERS) and has_execution:
        return ResidualFinding(
            "RV-003",
            "approval-gate bypass language with execution dispatch in same turn",
        )
    return None


def evaluate_residual(transcript_path: str | None, *, role: str) -> Decision | None:
    """Read the transcript and return a residual deny ``Decision`` or ``None``.

    Returns ``None`` when the transcript is clean (or legitimately empty). Returns
    a ``PC-008`` deny when the transcript cannot be read or parsed (fail-closed on
    an unverifiable audit), and an ``RV-###`` deny carrying a corrective
    ``additionalContext`` reroute when a residual violation is found.
    """
    if not transcript_path:
        return _unavailable("no transcript_path on envelope")
    try:
        events = read_transcript(transcript_path)
    except TranscriptUnavailableError as exc:
        return _unavailable(str(exc))
    except MalformedTranscriptError as exc:
        return _unavailable(str(exc))
    except EmptyTranscriptError:
        return None
    finding = run_residual_checks(events, role=role)
    if finding is None:
        return None
    return Decision(
        decision="deny",
        reason_id=finding.check_id,
        reason=f"{finding.check_id}: {finding.reason}",
        additional_context=_REROUTE,
    )


def _unavailable(detail: str) -> Decision:
    return Decision(
        decision="deny",
        reason_id=TRANSCRIPT_UNAVAILABLE_REASON_ID,
        reason=f"{TRANSCRIPT_UNAVAILABLE_REASON_ID}: transcript unavailable for "
        f"residual parity audit ({detail})",
        additional_context=_REROUTE,
    )
