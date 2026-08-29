#!/usr/bin/env python3
"""Helm hook shim for the PostToolUse event (Class B — agent-workflow gate).

All resilience and routing logic lives in :mod:`_helm_hook`; this shim only
declares the event's class and its event-native wire shapes. PostToolUse carries
its verdict in the ``{"decision":"block", "reason":…}`` shape.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _helm_hook  # noqa: E402

SPEC = _helm_hook.EventSpec(
    name="PostToolUse",
    event_class="B",
    allow={},
    deny_shape="block",
)


if __name__ == "__main__":
    sys.exit(_helm_hook.run(SPEC))
