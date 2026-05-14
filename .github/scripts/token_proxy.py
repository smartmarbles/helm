"""
mitmproxy addon — LLM API token usage interceptor
==================================================

Intercepts LLM API responses and captures real usage token counts that VS Code
discards before writing session JSON. Logs one JSONL entry per request to
~/.token_proxy_log.jsonl.

Providers intercepted:
  - api.githubcopilot.com / copilot-proxy.githubusercontent.com  (GitHub Copilot)
  - api.openai.com                                                (OpenAI)
  - openrouter.ai                                                 (OpenRouter)
  - api.anthropic.com                                             (Anthropic)
  - localhost:11434                                               (Ollama)
  - localhost:1234                                                (LM Studio)
  - localhost:8080                                                (llama.cpp)

Setup:
  pip install mitmproxy
  mitmdump -s token_proxy.py --listen-port 8888

Configure VS Code proxy:
  In settings.json:
    "http.proxy": "http://127.0.0.1:8888",
    "http.proxyStrictSSL": false

Trust mitmproxy CA cert (one-time):
  Run:  mitmproxy --listen-port 8888
  Visit: http://mitm.it in browser (while proxy is active)
  Install the cert for your OS / browser
  Windows shortcut: certutil -addstore Root ~/.mitmproxy/mitmproxy-ca-cert.cer

GitHub Copilot cert-pinning caveat:
  Copilot may use certificate pinning for api.githubcopilot.com.
  If interception fails (you see SSL errors or no log entries for Copilot),
  set "github.copilot.advanced": { "debug.overrideProxySupport": "on" } in settings.json.
  If still failing, Copilot is pinning — local providers (Ollama, LM Studio) will still work fine.

Testing:
  1. Start proxy:
       mitmdump -s .github/scripts/token_proxy.py --listen-port 8888

  2. Test local provider (Ollama — easiest, no TLS):
       curl -x http://127.0.0.1:8888 http://localhost:11434/api/chat \\
         -d '{"model":"llama3","messages":[{"role":"user","content":"hi"}],"stream":false}'
     Expect: entry appears in ~/.token_proxy_log.jsonl with provider="ollama"

  3. Test OpenAI-compat (requires OPENAI_API_KEY):
       curl -x http://127.0.0.1:8888 https://api.openai.com/v1/chat/completions \\
         -H "Authorization: Bearer $OPENAI_API_KEY" \\
         -H "Content-Type: application/json" \\
         -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"hi"}]}'
     Expect: entry with provider="openai"

  4. Verify log:
       python -c "
       import json, pathlib
       log = pathlib.Path.home() / '.token_proxy_log.jsonl'
       for line in log.read_text().splitlines()[-5:]:
           print(json.dumps(json.loads(line), indent=2))
       "

  5. Test VS Code integration:
     - Apply proxy settings above, restart VS Code
     - Run any Copilot Chat prompt
     - Check log — should see entries for copilot-proxy.githubusercontent.com or api.githubcopilot.com
"""

from __future__ import annotations

import json
import logging
import pathlib
import re
from datetime import datetime, timezone
from typing import Any

from mitmproxy import http
from mitmproxy.net.http import http1

LOG_PATH = pathlib.Path.home() / ".token_proxy_log.jsonl"

_PROVIDER_MAP: dict[str, str] = {
    "api.githubcopilot.com": "copilot",
    "copilot-proxy.githubusercontent.com": "copilot",
    "api.openai.com": "openai",
    "openrouter.ai": "openrouter",
    "api.anthropic.com": "anthropic",
    "localhost:11434": "ollama",
    "localhost:1234": "lmstudio",
    "localhost:8080": "llamacpp",
}

_LLM_PATH_RE = re.compile(
    r"/(v\d+/)?(chat/completions|completions|api/chat|api/generate|messages)$"
)

logging.basicConfig(level=logging.WARNING)
_log = logging.getLogger("token_proxy")


def _provider_for_host(host_header: str) -> str | None:
    h = host_header.lower().split(":")[0]
    for key, name in _PROVIDER_MAP.items():
        k_host = key.split(":")[0]
        if h == k_host or h.endswith("." + k_host):
            return name
    return None


def _is_llm_path(path: str) -> bool:
    return bool(_LLM_PATH_RE.search(path.split("?")[0]))


def _extract_model(body: dict[str, Any]) -> str:
    return str(body.get("model", "unknown"))


def _extract_usage_openai(body: dict[str, Any]) -> tuple[int, int]:
    usage = body.get("usage") or {}
    return int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))


def _extract_usage_anthropic(body: dict[str, Any]) -> tuple[int, int]:
    usage = body.get("usage") or {}
    return int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0))


def _extract_usage_ollama(body: dict[str, Any]) -> tuple[int, int]:
    return (
        int(body.get("prompt_eval_count", 0)),
        int(body.get("eval_count", 0)),
    )


def _parse_sse_chunks(raw: bytes) -> list[dict[str, Any]]:
    """Parse SSE stream; return all successfully decoded JSON data objects."""
    chunks: list[dict[str, Any]] = []
    for line in raw.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            continue
        try:
            chunks.append(json.loads(payload))
        except json.JSONDecodeError:
            pass
    return chunks


def _usage_from_sse_openai(chunks: list[dict[str, Any]]) -> tuple[int, int]:
    for chunk in reversed(chunks):
        usage = chunk.get("usage")
        if usage:
            return int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))
    return 0, 0


def _usage_from_sse_anthropic(chunks: list[dict[str, Any]]) -> tuple[int, int]:
    prompt = 0
    completion = 0
    for chunk in chunks:
        t = chunk.get("type", "")
        if t == "message_start":
            msg = chunk.get("message") or {}
            usage = msg.get("usage") or {}
            prompt = int(usage.get("input_tokens", prompt))
        elif t == "message_delta":
            usage = chunk.get("usage") or {}
            completion = int(usage.get("output_tokens", completion))
    return prompt, completion


def _write_log_entry(entry: dict[str, Any]) -> None:
    try:
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as exc:
        _log.error("Failed to write log entry: %s", exc)


def _make_entry(
    *,
    provider: str,
    host: str,
    path: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    status: int,
    error: str | None,
    request_id: str | None,
) -> dict[str, Any]:
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "host": host,
        "path": path,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "status": status,
        "error": error,
        "request_id": request_id,
    }


class TokenProxyAddon:
    def response(self, flow: http.HTTPFlow) -> None:
        if flow.response is None:
            return

        host_header = flow.request.pretty_host
        provider = _provider_for_host(host_header)
        if provider is None:
            return

        path = flow.request.path
        if not _is_llm_path(path):
            return

        status = flow.response.status_code
        request_id: str | None = flow.response.headers.get("x-request-id") or flow.request.headers.get("x-request-id")

        if status < 200 or status >= 300:
            _write_log_entry(
                _make_entry(
                    provider=provider,
                    host=host_header,
                    path=path,
                    model="unknown",
                    prompt_tokens=0,
                    completion_tokens=0,
                    status=status,
                    error=f"http_{status}",
                    request_id=request_id,
                )
            )
            return

        content_type = flow.response.headers.get("content-type", "")
        is_sse = "text/event-stream" in content_type

        try:
            raw_body = flow.response.get_content()
            model = "unknown"
            prompt_tokens = 0
            completion_tokens = 0

            if is_sse:
                chunks = _parse_sse_chunks(raw_body)
                if provider == "anthropic":
                    prompt_tokens, completion_tokens = _usage_from_sse_anthropic(chunks)
                    if chunks:
                        model = _extract_model(
                            (chunks[0].get("message") or {}) if chunks[0].get("type") == "message_start" else chunks[0]
                        )
                else:
                    prompt_tokens, completion_tokens = _usage_from_sse_openai(chunks)
                    for chunk in chunks:
                        m = chunk.get("model")
                        if m:
                            model = str(m)
                            break
            else:
                if not raw_body:
                    return
                body: dict[str, Any] = json.loads(raw_body.decode("utf-8", errors="replace"))
                model = _extract_model(body)
                if provider == "anthropic":
                    prompt_tokens, completion_tokens = _extract_usage_anthropic(body)
                elif provider == "ollama":
                    prompt_tokens, completion_tokens = _extract_usage_ollama(body)
                else:
                    prompt_tokens, completion_tokens = _extract_usage_openai(body)

            _write_log_entry(
                _make_entry(
                    provider=provider,
                    host=host_header,
                    path=path,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    status=status,
                    error=None,
                    request_id=request_id,
                )
            )

        except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError, ValueError) as exc:
            _log.warning("parse_failed for %s%s: %s", host_header, path, exc)
            _write_log_entry(
                _make_entry(
                    provider=provider,
                    host=host_header,
                    path=path,
                    model="unknown",
                    prompt_tokens=0,
                    completion_tokens=0,
                    status=status,
                    error="parse_failed",
                    request_id=request_id,
                )
            )


def load(loader):  # noqa: ANN001 — mitmproxy hook signature
    pass


addon = TokenProxyAddon()
addons = [addon]
