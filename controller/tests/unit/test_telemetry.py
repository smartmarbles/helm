"""Tests for the telemetry emitter (spec015 Task 8.3 / 8.5).

Telemetry is best-effort observability: a misbehaving sink MUST NOT break policy
enforcement. These tests cover each signal shape, the disabled no-op branch, and
the emission-failure error-logging branch.
"""

from __future__ import annotations

import logging

import pytest

from helm_controller.audit.telemetry import TelemetryEmitter, TelemetrySignal


class _RecordingSink:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def __call__(self, event: dict) -> None:
        self.events.append(event)


@pytest.mark.parametrize("signal", list(TelemetrySignal))
def test_each_signal_emits_expected_shape(signal: TelemetrySignal) -> None:
    sink = _RecordingSink()
    emitter = TelemetryEmitter(sink)
    emitter.emit(signal, session_id="s", turn_id="t")
    assert sink.events == [
        {"signal": signal.value, "session_id": "s", "turn_id": "t"}
    ]


def test_disabled_emitter_is_noop() -> None:
    sink = _RecordingSink()
    emitter = TelemetryEmitter(sink, enabled=False)
    emitter.emit(TelemetrySignal.DECISION_EMITTED, session_id="s")
    assert sink.events == []


def test_default_sink_is_noop_and_does_not_raise() -> None:
    emitter = TelemetryEmitter()
    emitter.emit(TelemetrySignal.RESIDUAL_VIOLATION, check_id="RV-001")


def test_sink_failure_is_logged_not_propagated(caplog) -> None:
    def boom(_event: dict) -> None:
        raise RuntimeError("sink exploded")

    logger = logging.getLogger("helm_controller.audit.telemetry.test")
    emitter = TelemetryEmitter(boom, logger=logger)
    with caplog.at_level(logging.ERROR, logger=logger.name):
        emitter.emit(TelemetrySignal.SPLIT_PLANE_DIVERGENCE, session_id="s")
    assert "telemetry sink failed" in caplog.text
    assert "split_plane_divergence" in caplog.text


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
