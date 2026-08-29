#!/usr/bin/env python3
"""Helm hook shim for the UserPromptSubmit event (Class A — human-conversational).

All resilience and routing logic lives in :mod:`_helm_hook`; this shim only
declares the event's class and its event-native wire shapes. As a Class-A event
it is NEVER hard-denied — blocking it would brick the human's prompt, the exact
failure this design exists to prevent.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _helm_hook  # noqa: E402

SPEC = _helm_hook.EventSpec(
    name="UserPromptSubmit",
    event_class="A",
    allow={},
    deny_shape="common",
)


if __name__ == "__main__":
    sys.exit(_helm_hook.run(SPEC))
