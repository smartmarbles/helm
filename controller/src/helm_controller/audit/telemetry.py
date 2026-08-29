"""Telemetry signals for the decision pipeline (spec015 Task 8.3).

Telemetry is best-effort observability: a misbehaving sink MUST NOT break policy
enforcement. Every emission therefore runs under a guard that swallows sink
failures into the error log rather than propagating them up the hot path. When
the emitter is disabled the call is a pure no-op (no sink invocation, no event
construction side effects).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from enum import Enum

_LOGGER = logging.getLogger("helm_controller.audit.telemetry")

Sink = Callable[[dict], None]


class TelemetrySignal(str, Enum):
    """The signal types the pipeline emits."""

    DECISION_EMITTED = "decision_emitted"
    SPLIT_PLANE_DIVERGENCE = "split_plane_divergence"
    RESIDUAL_VIOLATION = "residual_violation"


def _noop_sink(_event: dict) -> None:
    return None


class TelemetryEmitter:
    """Emits structured telemetry events to a sink, fail-safe by construction."""

    def __init__(
        self,
        sink: Sink | None = None,
        *,
        enabled: bool = True,
        logger: logging.Logger = _LOGGER,
    ) -> None:
        self._sink = sink or _noop_sink
        self._enabled = enabled
        self._logger = logger

    def emit(self, signal: TelemetrySignal, **fields: object) -> None:
        """Emit *signal* with *fields*; never raises on sink failure."""
        if not self._enabled:
            return
        event = {"signal": signal.value, **fields}
        try:
            self._sink(event)
        except Exception:  # noqa: BLE001 - observability must not break enforcement
            self._logger.exception("telemetry sink failed for signal %s", signal.value)
