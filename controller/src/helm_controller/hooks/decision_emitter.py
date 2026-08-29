"""Decision emitter — thin composition of pipeline decision + wire adapter.

spec015 Task 8.2. This is intentionally thin: the policy work lives in
:mod:`helm_controller.hooks.pipeline` (the decision) and
:mod:`helm_controller.hooks.response_adapter` (the wire shape). The emitter
joins them into the single value the transport layer returns as the HTTP
response body, and offers a JSON serialization for the stdout hook path.

Fail-closed: a ``None`` decision is never serialized as an empty pass-through;
:func:`~helm_controller.hooks.response_adapter.to_wire` converts it into a
cross-family deny (Watch Out #15).
"""

from __future__ import annotations

import json
from collections.abc import Callable

from helm_controller.contracts.decision import Decision
from helm_controller.hooks.response_adapter import to_wire


class DecisionEmitter:
    """Compose an internal :class:`Decision` into a VS Code-native wire dict."""

    def __init__(
        self, adapter: Callable[[str | None, Decision | None], dict] = to_wire
    ) -> None:
        self._adapter = adapter

    def emit(self, hook_event: str | None, decision: Decision | None) -> dict:
        """Return the native wire dict for *decision* under *hook_event*."""
        return self._adapter(hook_event, decision)

    def emit_json(self, hook_event: str | None, decision: Decision | None) -> str:
        """Return the native wire dict serialized as a compact JSON string."""
        return json.dumps(self.emit(hook_event, decision), separators=(",", ":"))
