"""Localhost HTTP transport for the Helm controller.

Exposes a single ``POST /hook`` endpoint that Python hook wrappers call. Uses
:class:`http.server.ThreadingHTTPServer` so concurrent hook events from multiple
VS Code Agent panes are each handled on an independent thread (two panes can fire
``PreToolUse`` within the same wall-clock second).

Routing to the decision pipeline is injected as a callable so the transport
stays decoupled from policy. The real handler is composed in
:mod:`helm_controller.hooks.decision_service` (Phase 8) and produces the VS
Code-native wire shape via the response adapter; this transport echoes that
body verbatim and never inspects the decision vocabulary.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, cast

_LOGGER = logging.getLogger("helm_controller.transport")

DecisionHandler = Callable[[dict[str, Any]], dict[str, Any]]

_HOOK_PATH = "/hook"
_FAIL_CLOSED_DENY: dict[str, Any] = {
    "decision": "deny",
    "reason": "controller error (PC-004)",
}


class _HookRequestHandler(BaseHTTPRequestHandler):
    server_version = "HelmController/0.1"
    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:  # noqa: N802 - name fixed by BaseHTTPRequestHandler
        if self.path != _HOOK_PATH:
            self._respond(404, _FAIL_CLOSED_DENY)
            return
        try:
            payload = json.loads(self._read_body())
        except (ValueError, OSError):
            self._respond(400, _FAIL_CLOSED_DENY)
            return
        handler = cast("HookHTTPServer", self.server).decision_handler
        try:
            decision = handler(payload)
        except Exception:
            _LOGGER.exception("Decision handler raised; failing closed.")
            self._respond(500, _FAIL_CLOSED_DENY)
            return
        self._respond(200, decision)

    def _read_body(self) -> str:
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length).decode("utf-8")

    def _respond(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        _LOGGER.debug("%s - %s", self.address_string(), format % args)


class HookHTTPServer(ThreadingHTTPServer):
    """``ThreadingHTTPServer`` carrying the injected decision handler."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        decision_handler: DecisionHandler,
    ) -> None:
        super().__init__(server_address, _HookRequestHandler)
        self.decision_handler = decision_handler


def create_server(
    bind_address: str,
    port: int,
    decision_handler: DecisionHandler,
) -> HookHTTPServer:
    """Bind a :class:`HookHTTPServer` on ``bind_address:port``.

    ``port`` 0 lets the OS assign a free port; read the actual port back from
    ``server.server_address[1]`` after binding.
    """
    return HookHTTPServer((bind_address, port), decision_handler)
