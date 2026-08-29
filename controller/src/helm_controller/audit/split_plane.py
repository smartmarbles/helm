"""Split-plane recording — Python allowed, VS Code natively rejected (Task 8.3).

Some outcomes are decided outside the Python controller: VS Code can reject a
tool call the controller allowed (the user clicks deny on the permission prompt)
or a Stop after the controller said allow. That divergence is the "split plane".
It is recorded as a turn-level audit fact, and — critically — the FSM MUST NOT
advance on a native rejection: the attempted transition simply did not happen, so
the runtime FSM state is left untouched (``fsm_advanced`` is always ``False``).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from helm_controller.audit.telemetry import TelemetryEmitter, TelemetrySignal

PYTHON_ALLOW = "allow"
NATIVE_REJECT = "reject"


@dataclass(frozen=True)
class SplitPlaneRecord:
    """A turn-level audit fact: controller allowed, VS Code natively rejected."""

    session_id: str
    workflow_id: str | None
    turn_id: str
    hook_event: str
    python_decision: str
    native_outcome: str
    fsm_advanced: bool
    reason: str | None


Recorder = Callable[[SplitPlaneRecord], None]


def record_split_plane(
    *,
    recorder: Recorder,
    telemetry: TelemetryEmitter,
    session_id: str,
    workflow_id: str | None,
    turn_id: str,
    hook_event: str,
    reason: str | None = None,
) -> SplitPlaneRecord:
    """Record an allow/native-reject divergence without advancing the FSM."""
    record = SplitPlaneRecord(
        session_id=session_id,
        workflow_id=workflow_id,
        turn_id=turn_id,
        hook_event=hook_event,
        python_decision=PYTHON_ALLOW,
        native_outcome=NATIVE_REJECT,
        fsm_advanced=False,
        reason=reason,
    )
    recorder(record)
    telemetry.emit(
        TelemetrySignal.SPLIT_PLANE_DIVERGENCE,
        session_id=session_id,
        workflow_id=workflow_id,
        turn_id=turn_id,
        hook_event=hook_event,
        reason=reason,
    )
    return record
