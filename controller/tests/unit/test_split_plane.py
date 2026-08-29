"""Tests for split-plane recording (spec015 Task 8.3 / 8.5).

A split plane is a turn where the Python controller allowed but VS Code natively
rejected. It is recorded as a turn-level audit fact and — critically — the FSM
MUST NOT advance: ``fsm_advanced`` is always ``False``. Both the audit recorder
and the telemetry signal must fire.
"""

from __future__ import annotations

import pytest

from helm_controller.audit.split_plane import (
    NATIVE_REJECT,
    PYTHON_ALLOW,
    SplitPlaneRecord,
    record_split_plane,
)
from helm_controller.audit.telemetry import TelemetryEmitter, TelemetrySignal


class _RecordingSink:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def __call__(self, event: dict) -> None:
        self.events.append(event)


def _telemetry() -> tuple[TelemetryEmitter, _RecordingSink]:
    sink = _RecordingSink()
    return TelemetryEmitter(sink), sink


def test_records_audit_fact_without_advancing_fsm() -> None:
    recorded: list[SplitPlaneRecord] = []
    telemetry, _sink = _telemetry()
    record = record_split_plane(
        recorder=recorded.append,
        telemetry=telemetry,
        session_id="s",
        workflow_id="w",
        turn_id="t",
        hook_event="PreToolUse",
        reason="user clicked deny",
    )
    assert recorded == [record]
    assert record.python_decision == PYTHON_ALLOW
    assert record.native_outcome == NATIVE_REJECT
    assert record.fsm_advanced is False
    assert record.reason == "user clicked deny"


def test_emits_split_plane_divergence_signal() -> None:
    telemetry, sink = _telemetry()
    record_split_plane(
        recorder=lambda _r: None,
        telemetry=telemetry,
        session_id="s",
        workflow_id="w",
        turn_id="t",
        hook_event="Stop",
        reason="native reject",
    )
    assert len(sink.events) == 1
    event = sink.events[0]
    assert event["signal"] == TelemetrySignal.SPLIT_PLANE_DIVERGENCE.value
    assert event["session_id"] == "s"
    assert event["hook_event"] == "Stop"


def test_both_signals_recorded_and_reason_defaults_to_none() -> None:
    recorded: list[SplitPlaneRecord] = []
    telemetry, sink = _telemetry()
    record = record_split_plane(
        recorder=recorded.append,
        telemetry=telemetry,
        session_id="s",
        workflow_id=None,
        turn_id="t",
        hook_event="SubagentStop",
    )
    assert len(recorded) == 1
    assert len(sink.events) == 1
    assert record.reason is None
    assert record.workflow_id is None


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
