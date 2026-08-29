"""100%-branch tests for the localhost HTTP transport (Task 3.0).

The server is exercised end-to-end over a real loopback socket via
:class:`http.client.HTTPConnection`, so routing, status codes, the injected
decision-handler seam, fail-closed behavior, and per-thread dispatch are all
verified against actual ``ThreadingHTTPServer`` semantics rather than mocks.
"""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from http.client import HTTPConnection

from helm_controller import server as server_module
from helm_controller.transport.http_server import (
    _FAIL_CLOSED_DENY,
    create_server,
)


@contextmanager
def _serve(handler):
    srv = create_server("127.0.0.1", 0, handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield srv.server_address[1]
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=5)


def _post(port, path, body, *, raw=False):
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        data = body if raw else json.dumps(body)
        conn.request(
            "POST", path, body=data, headers={"Content-Type": "application/json"}
        )
        resp = conn.getresponse()
        return resp.status, resp.read().decode("utf-8")
    finally:
        conn.close()


def _request(port, method, path):
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        conn.request(method, path)
        resp = conn.getresponse()
        return resp.status, resp.read().decode("utf-8")
    finally:
        conn.close()


# --- Happy path + decision-handler seam ------------------------------------


def test_valid_payload_returns_200_with_decision_json() -> None:
    decision = {"decision": "ask", "reason": "needs approval"}
    with _serve(lambda payload: decision) as port:
        status, body = _post(port, "/hook", {"hook_event": "PreToolUse"})
    assert status == 200
    assert json.loads(body) == decision


def test_decision_handler_receives_parsed_payload() -> None:
    seen: list[dict] = []

    def handler(payload):
        seen.append(payload)
        return {"decision": "allow", "reason": "ok"}

    sent = {"hook_event": "PostToolUse", "sessionId": "s-1"}
    with _serve(handler) as port:
        status, _ = _post(port, "/hook", sent)
    assert status == 200
    assert seen == [sent]


# --- Error paths (all fail closed with deny, never allow) -------------------


def test_malformed_body_returns_400_fail_closed_deny() -> None:
    with _serve(lambda payload: {"decision": "allow"}) as port:
        status, body = _post(port, "/hook", "not-json{", raw=True)
    assert status == 400
    assert json.loads(body) == _FAIL_CLOSED_DENY
    assert json.loads(body)["decision"] == "deny"


def test_unknown_path_returns_404_fail_closed_deny() -> None:
    with _serve(lambda payload: {"decision": "allow"}) as port:
        status, body = _post(port, "/nope", {"hook_event": "Stop"})
    assert status == 404
    assert json.loads(body) == _FAIL_CLOSED_DENY


def test_wrong_method_is_not_served() -> None:
    # do_POST is the only handler; a GET is rejected by BaseHTTPRequestHandler
    # (501) rather than silently served — it never reaches a decision.
    with _serve(lambda payload: {"decision": "allow"}) as port:
        status, _ = _request(port, "GET", "/hook")
    assert status == 501


def test_handler_exception_returns_500_fail_closed_deny() -> None:
    def boom(payload):
        raise RuntimeError("pipeline blew up")

    with _serve(boom) as port:
        status, body = _post(port, "/hook", {"hook_event": "PreToolUse"})
    assert status == 500
    assert json.loads(body) == _FAIL_CLOSED_DENY


def test_empty_handler_output_is_not_coerced_to_allow() -> None:
    # Watch Out #15: an unrecognized/empty handler result must NOT be silently
    # treated as allow. The transport returns it verbatim; it injects no allow.
    with _serve(lambda payload: {}) as port:
        status, body = _post(port, "/hook", {"hook_event": "PreToolUse"})
    assert status == 200
    parsed = json.loads(body)
    assert parsed == {}
    assert parsed.get("decision") != "allow"


# --- Concurrency: ThreadingHTTPServer dispatches per-thread ------------------


def test_concurrent_requests_do_not_interleave() -> None:
    def handler(payload):
        return {"decision": "allow", "echo": payload["id"]}

    results: dict[int, int] = {}
    lock = threading.Lock()

    with _serve(handler) as port:

        def fire(i: int) -> None:
            status, body = _post(port, "/hook", {"id": i})
            with lock:
                results[i] = json.loads(body)["echo"]

        threads = [threading.Thread(target=fire, args=(i,)) for i in range(20)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)

    assert results == {i: i for i in range(20)}


# --- Port-file write on bind / removal on shutdown (server.py helpers) ------


def test_write_port_file_writes_integer_content(tmp_path) -> None:
    port_file = tmp_path / ".helm-controller.port"
    server_module._write_port_file(port_file, 54321)
    assert port_file.read_text(encoding="utf-8") == "54321"


def test_remove_port_file_deletes_existing(tmp_path) -> None:
    port_file = tmp_path / ".helm-controller.port"
    port_file.write_text("1", encoding="utf-8")
    server_module._remove_port_file(port_file)
    assert not port_file.exists()


def test_remove_port_file_missing_is_noop(tmp_path) -> None:
    port_file = tmp_path / "absent.port"
    server_module._remove_port_file(port_file)  # must not raise
    assert not port_file.exists()
