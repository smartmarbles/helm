#!/usr/bin/env python3
"""Helm hook shim for the SessionStart event (Class A — human-conversational).

All resilience and routing logic lives in :mod:`_helm_hook`; this shim only
declares the event's class and its event-native wire shapes. As a Class-A event
it is never hard-denied: a controller deny degrades to a non-blocking pass.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _helm_hook  # noqa: E402

SPEC = _helm_hook.EventSpec(
    name="SessionStart",
    event_class="A",
    allow={},
    deny_shape="common",
)


if __name__ == "__main__":
    sys.exit(_helm_hook.run(SPEC))
