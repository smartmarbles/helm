#!/usr/bin/env python3
"""
copilot_token_analyzer.py
=========================
Analyzes GitHub Copilot Chat session logs to report per-turn token usage.

Handles three sources:
  1. Raw chatSessions JSON files  (auto-discovered from VS Code workspaceStorage)
  2. Exported chat JSON files     (from Command Palette → "Chat: Export Chat...")
  3. Agent JSONL files            (CLI / background-agent sessions)

Usage:
  python copilot_token_analyzer.py                              # auto-discover all sessions
  python copilot_token_analyzer.py --file session.json         # single file
  python copilot_token_analyzer.py --dir /path/to/dir          # scan a directory
  python copilot_token_analyzer.py --summary                   # totals only, no per-turn detail
  python copilot_token_analyzer.py --days 7                    # only sessions from last N days
  python copilot_token_analyzer.py --compare baseline.json optimized.json   # diff two sessions

Install optional dependency for accurate tokenization:
  pip install tiktoken
"""

import argparse
import io
import json
import os
import platform
import re
import sys
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Token estimation ──────────────────────────────────────────────────────────
try:
    import tiktoken
    _ENCODERS: dict = {}

    def estimate_tokens(text: str, model: str = "gpt-4o") -> int:
        """Use tiktoken for accurate token counting."""
        if not text:
            return 0
        enc_name = model if model in ("gpt-4o", "gpt-4", "gpt-3.5-turbo") else "gpt-4o"
        if enc_name not in _ENCODERS:
            try:
                _ENCODERS[enc_name] = tiktoken.encoding_for_model(enc_name)
            except KeyError:
                _ENCODERS[enc_name] = tiktoken.get_encoding("cl100k_base")
        return len(_ENCODERS[enc_name].encode(text))

    TIKTOKEN_AVAILABLE = True

except ImportError:
    def estimate_tokens(text: str, model: str = "gpt-4o") -> int:
        """Fallback: characters × 0.25 ≈ tokens (rough but consistent)."""
        return max(1, int(len(text or "") * 0.25))

    TIKTOKEN_AVAILABLE = False


# ── OS path discovery ─────────────────────────────────────────────────────────
def get_vscode_paths() -> list[Path]:
    """Return all plausible VS Code user-data directories for this platform."""
    system = platform.system()
    candidates = []

    if system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            base = Path(appdata)
            candidates += [
                base / "Code" / "User",
                base / "Code - Insiders" / "User",
                base / "VSCodium" / "User",
            ]
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
        candidates += [
            base / "Code" / "User",
            base / "Code - Insiders" / "User",
            base / "VSCodium" / "User",
        ]
    else:  # Linux / WSL
        xdg = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        base = Path(xdg)
        candidates += [
            base / "Code" / "User",
            base / "Code - Insiders" / "User",
            base / "VSCodium" / "User",
        ]

    return [p for p in candidates if p.exists()]


def find_session_files(base_dirs: list[Path] | None = None) -> list[Path]:
    """
    Recursively scan workspaceStorage for Copilot Chat session files (.json / .jsonl).
    Also checks ~/.copilot/session-state for CLI agent sessions.
    """
    if base_dirs is None:
        base_dirs = get_vscode_paths()

    found: list[Path] = []

    for base in base_dirs:
        ws_storage = base / "workspaceStorage"
        if ws_storage.exists():
            # chatSessions live inside workspaceStorage/<hash>/GitHub.copilot-chat/chatSessions/
            for f in ws_storage.rglob("*.json"):
                if (len(f.parts) >= 3 and "copilot" in f.parts[-3].lower()) or "chatSessions" in str(f):
                    found.append(f)
            for f in ws_storage.rglob("*.jsonl"):
                found.append(f)

    # Copilot CLI agent sessions
    cli_path = Path.home() / ".copilot" / "session-state"
    if cli_path.exists():
        found += list(cli_path.rglob("*.jsonl"))
        found += list(cli_path.rglob("*.json"))

    return sorted(set(found))


# ── Parsers ───────────────────────────────────────────────────────────────────

def _extract_text(value) -> str:
    """Flatten a content value to plain text regardless of its structure."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("text", item.get("value", "")))
        return " ".join(parts)
    if isinstance(value, dict):
        return value.get("text", value.get("value", str(value)))
    return str(value) if value else ""


def parse_exported_chat(data: dict) -> list[dict]:
    """
    Parse the format produced by "Chat: Export Chat..." command.
    Top-level keys: "version", "sessions" (list) or flat array of turns.
    Each turn has "type"/"role" + "message"/"value"/"content".
    """
    turns = []
    raw_turns = []

    if isinstance(data, list):
        raw_turns = data
    elif "sessions" in data:
        for session in data["sessions"]:
            raw_turns += session.get("turns", session.get("requests", []))
    elif "turns" in data:
        raw_turns = data["turns"]
    elif "requests" in data:
        raw_turns = data["requests"]

    model = data.get("model", "unknown") if isinstance(data, dict) else "unknown"

    for i, turn in enumerate(raw_turns):
        if not isinstance(turn, dict):
            continue

        role = turn.get("type", turn.get("role", "")).lower()
        content_raw = (
            turn.get("message")
            or turn.get("value")
            or turn.get("content")
            or turn.get("response")
            or ""
        )
        content = _extract_text(content_raw)
        turn_model = turn.get("model", turn.get("modelId", model))

        if not content.strip():
            continue

        turns.append({
            "turn": i + 1,
            "role": role if role else ("user" if i % 2 == 0 else "assistant"),
            "model": turn_model or "unknown",
            "content": content,
            "tokens": estimate_tokens(content, turn_model or "gpt-4o"),
        })

        # Tool calls embedded in exported chat turns
        tool_calls = turn.get("toolCalls") or turn.get("subagentCalls") or []
        for j, tc in enumerate(tool_calls):
            if not isinstance(tc, dict):
                continue
            tc_input  = json.dumps(tc.get("input", tc.get("arguments", {})))
            tc_output = _extract_text(tc.get("output") or tc.get("result") or "")
            tc_name   = tc.get("name", tc.get("toolName", f"tool_{j}"))
            if tc_input.strip() and tc_input != "{}":
                turns.append({
                    "turn": i + 1,
                    "role": f"tool_call({tc_name})",
                    "model": turn_model or "unknown",
                    "content": tc_input,
                    "tokens": estimate_tokens(tc_input, turn_model or "gpt-4o"),
                })
            if tc_output.strip():
                turns.append({
                    "turn": i + 1,
                    "role": f"tool_result({tc_name})",
                    "model": turn_model or "unknown",
                    "content": tc_output,
                    "tokens": estimate_tokens(tc_output, turn_model or "gpt-4o"),
                })

    return turns


# ── Orchestrator constraint enforcement ──────────────────────────────────────

# Tools ARTHUR's instructions explicitly forbid him from calling directly.
# A root-level call to any of these is a candidate behavioral violation.
ARTHUR_FORBIDDEN_TOOLS = {
    "create_file",
    "replace_string_in_file",
    "multi_replace_string_in_file",
    "edit_notebook_file",
    "create_new_jupyter_notebook",
    "create_new_workspace",
    "run_in_terminal",
    "execution_subagent",
    "create_and_run_task",
    "install_extension",
    "run_vscode_command",
    # VS Code internal equivalents
    "copilot_createFile",
    "copilot_replaceString",
    "copilot_runInTerminal",
}


def _extract_tool_invocations(response_raw: list, model: str, turn_number: int) -> list[dict]:
    """
    Walk a VS Code response list and extract toolInvocationSerialized items as turn dicts.

    VS Code stores tool calls inline in the response array rather than in a separate
    "toolCalls" key, using items with kind=="toolInvocationSerialized".  Each item has:
      - toolId          : tool name
      - toolCallId      : unique ID (children reference this via subAgentInvocationId)
      - subAgentInvocationId : set on nested calls — links them to their parent subagent
      - invocationMessage   : call description (dict with "value" key, or plain string)
      - pastTenseMessage    : result description (same shapes)
      - toolSpecificData    : for runSubagent: {kind:"subagent", agentName, prompt, result, modelName}

    Produces turns with roles:
      tool_call(AGENTNAME)          / tool_result(AGENTNAME)          — runSubagent calls
      tool_call(AGENTNAME/toolId)   / tool_result(AGENTNAME/toolId)   — nested calls
      tool_call(toolId)             / tool_result(toolId)             — root-level calls
    """
    if not isinstance(response_raw, list):
        return []

    # Pass 1: build toolCallId → agentName map for all runSubagent invocations.
    # Also detect untagged execution_subagent calls: if ARTHUR called execution_subagent
    # directly (no subAgentInvocationId), all other untagged calls in this response are
    # nested inside ARTHUR's own execution context — confirmed violations, not tagging gaps.
    subagent_map: dict[str, tuple] = {}  # toolCallId → (agentName, modelName)
    has_untagged_exec_subagent = False
    for item in response_raw:
        if not isinstance(item, dict) or item.get("kind") != "toolInvocationSerialized":
            continue
        tsd = item.get("toolSpecificData") or {}
        if isinstance(tsd, dict) and tsd.get("kind") == "subagent":
            tc_id = item.get("toolCallId", "")
            if tc_id:
                subagent_map[tc_id] = (
                    tsd.get("agentName", "unknown"),
                    tsd.get("modelName") or model,  # inherit request model if not set
                )
        if (item.get("toolId") == "execution_subagent"
                and not item.get("subAgentInvocationId")):
            has_untagged_exec_subagent = True

    # Pass 2: emit turn dicts
    turns: list[dict] = []
    for item in response_raw:
        if not isinstance(item, dict) or item.get("kind") != "toolInvocationSerialized":
            continue

        tool_id       = item.get("toolId", "unknown")
        sub_agent_id  = item.get("subAgentInvocationId", "")
        tsd           = item.get("toolSpecificData") or {}

        # Determine role names and model
        if isinstance(tsd, dict) and tsd.get("kind") == "subagent":
            # This IS a runSubagent call — label by agent name
            agent_name  = tsd.get("agentName", "unknown")
            call_role   = f"tool_call({agent_name})"
            result_role = f"tool_result({agent_name})"
            item_model  = tsd.get("modelName", model)
        elif sub_agent_id and sub_agent_id in subagent_map:
            # Nested call made BY a subagent — use the subagent's own model, not
            # the parent request model, so per-model totals reflect actual usage.
            parent, parent_model = subagent_map[sub_agent_id]
            call_role   = f"tool_call({parent}/{tool_id})"
            result_role = f"tool_result({parent}/{tool_id})"
            item_model  = parent_model
        else:
            # Root-level tool call — no subAgentInvocationId present.
            # [root~]/ = confirmed violation: response context is tainted (ARTHUR called
            #   execution_subagent directly) AND this tool is on the forbidden list.
            # [root]/  = clean root call: either the response is untainted, or the tool
            #   is allowed even at root level (e.g. copilot_readFile, manage_todo_list).
            if has_untagged_exec_subagent and tool_id in ARTHUR_FORBIDDEN_TOOLS:
                call_role   = f"tool_call([root~]/{tool_id})"
                result_role = f"tool_result([root~]/{tool_id})"
            else:
                call_role   = f"tool_call([root]/{tool_id})"
                result_role = f"tool_result([root]/{tool_id})"
            item_model  = model

        # Call content
        if isinstance(tsd, dict) and tsd.get("kind") == "subagent":
            call_text = tsd.get("prompt", "") or ""
        else:
            inv = item.get("invocationMessage", "")
            call_text = inv.get("value", "") if isinstance(inv, dict) else (str(inv) if inv else "")

        # Result content
        if isinstance(tsd, dict) and tsd.get("kind") == "subagent":
            result_text = tsd.get("result", "") or ""
        else:
            past = item.get("pastTenseMessage", "")
            result_text = past.get("value", "") if isinstance(past, dict) else (str(past) if past else "")
            # Fallback: resultDetails as JSON
            if not result_text.strip():
                rd = item.get("resultDetails")
                if rd:
                    result_text = json.dumps(rd)

        if call_text.strip():
            turns.append({
                "turn": turn_number,
                "role": call_role,
                "model": item_model,
                "content": call_text,
                "tokens": estimate_tokens(call_text, item_model),
            })
        if result_text.strip():
            turns.append({
                "turn": turn_number,
                "role": result_role,
                "model": item_model,
                "content": result_text,
                "tokens": estimate_tokens(result_text, item_model),
            })

    return turns


def parse_raw_session(data: dict) -> list[dict]:
    """
    Parse raw chatSessions JSON (VS Code internal format).
    Keys vary by version; common patterns below.
    """
    turns = []

    # Collect all requests/responses at any nesting level
    requests = (
        data.get("requests")
        or data.get("history")
        or data.get("conversations")
        or data.get("messages")
        or []
    )

    for i, req in enumerate(requests):
        if not isinstance(req, dict):
            continue

        model = req.get("model", req.get("modelId", "unknown"))

        # ── User message ──
        user_text = _extract_text(
            req.get("message")
            or req.get("prompt")
            or req.get("userMessage")
            or req.get("input")
            or ""
        )
        if user_text.strip():
            turns.append({
                "turn": i + 1,
                "role": "user",
                "model": model,
                "content": user_text,
                "tokens": estimate_tokens(user_text, model),
            })

        # ── Assistant response ──
        response = req.get("response") or req.get("result") or req.get("output") or {}
        if isinstance(response, str):
            resp_text = response
        elif isinstance(response, dict):
            resp_text = _extract_text(
                response.get("value")
                or response.get("message")
                or response.get("text")
                or response.get("content")
                or ""
            )
            model = response.get("model", response.get("modelId", model))
        elif isinstance(response, list):
            resp_text = _extract_text(response)
        else:
            resp_text = ""

        if resp_text.strip():
            turns.append({
                "turn": i + 1,
                "role": "assistant",
                "model": model,
                "content": resp_text,
                "tokens": estimate_tokens(resp_text, model),
            })

        # ── Sub-agent / tool calls (legacy key-based format) ──
        tool_calls = req.get("toolCalls") or req.get("subagentCalls") or []
        for j, tc in enumerate(tool_calls):
            if not isinstance(tc, dict):
                continue
            tc_input = json.dumps(tc.get("input", tc.get("arguments", {})))
            tc_output = _extract_text(tc.get("output") or tc.get("result") or "")
            tc_name = tc.get("name", tc.get("toolName", f"tool_{j}"))

            if tc_input.strip() and tc_input != "{}":
                turns.append({
                    "turn": i + 1,
                    "role": f"tool_call({tc_name})",
                    "model": model,
                    "content": tc_input,
                    "tokens": estimate_tokens(tc_input, model),
                })
            if tc_output.strip():
                turns.append({
                    "turn": i + 1,
                    "role": f"tool_result({tc_name})",
                    "model": model,
                    "content": tc_output,
                    "tokens": estimate_tokens(tc_output, model),
                })

        # ── Inline tool invocations (VS Code toolInvocationSerialized format) ──
        response_raw = req.get("response") or req.get("result") or req.get("output") or {}
        if isinstance(response_raw, list):
            turns += _extract_tool_invocations(response_raw, model, i + 1)

    return turns


def parse_jsonl(lines: list[str]) -> list[dict]:
    """
    Parse CLI / agent .jsonl files.
    Each line is a streaming delta or a full event object.
    """
    turns = []
    buffers: dict[str, list[str]] = {}
    model = "unknown"

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        event_type = event.get("type", "")
        model = event.get("model", event.get("modelId", model))
        role = event.get("role", "")

        # streaming delta
        if event_type == "content_block_delta":
            delta = event.get("delta", {})
            text = delta.get("text", "")
            key = f"block_{event.get('index', 0)}"
            buffers.setdefault(key, []).append(text)

        # end of a block — flush
        elif event_type == "content_block_stop":
            key = f"block_{event.get('index', 0)}"
            if key in buffers:
                full = "".join(buffers.pop(key))
                if full.strip():
                    turns.append({
                        "turn": len(turns) + 1,
                        "role": role or "assistant",
                        "model": model,
                        "content": full,
                        "tokens": estimate_tokens(full, model),
                    })

        # usage summary line
        elif event_type == "message_delta" and "usage" in event:
            pass  # actual counts from API — we use our estimates for consistency

        # tool use
        elif event_type == "tool_use" or event.get("tool_name"):
            name = event.get("name", event.get("tool_name", "tool"))
            inp = json.dumps(event.get("input", event.get("arguments", {})))
            turns.append({
                "turn": len(turns) + 1,
                "role": f"tool_call({name})",
                "model": model,
                "content": inp,
                "tokens": estimate_tokens(inp, model),
            })

        # plain message objects
        elif role in ("user", "assistant") and "content" in event:
            text = _extract_text(event["content"])
            if text.strip():
                turns.append({
                    "turn": len(turns) + 1,
                    "role": role,
                    "model": model,
                    "content": text,
                    "tokens": estimate_tokens(text, model),
                })

    # Flush any streaming blocks that ended without a content_block_stop event
    for key in sorted(buffers):
        full = "".join(buffers[key])
        if full.strip():
            turns.append({
                "turn": len(turns) + 1,
                "role": "assistant",
                "model": model,
                "content": full,
                "tokens": estimate_tokens(full, model),
            })

    return turns


def parse_file(path: Path) -> list[dict]:
    """Detect format and parse a session file. Returns list of turn dicts."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"  ⚠  Cannot read {path}: {e}", file=sys.stderr)
        return []

    if path.suffix == ".jsonl":
        return parse_jsonl(raw.splitlines())

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Might be concatenated JSON — try line-by-line
        return parse_jsonl(raw.splitlines())

    if not data:
        return []

    # Use raw_session parser when requests/history are present (handles toolCalls).
    # Fall back to exported_chat for list-format or sessions-keyed exports.
    if isinstance(data, dict) and any(k in data for k in ("requests", "history", "conversations", "messages")):
        turns = parse_raw_session(data)
        if not turns:
            turns = parse_exported_chat(data)
    elif isinstance(data, list) or (isinstance(data, dict) and "sessions" in data):
        turns = parse_exported_chat(data)
        if not turns:
            turns = parse_raw_session(data)
    else:
        turns = parse_exported_chat(data)
        if not turns:
            turns = parse_raw_session(data)

    return turns


# ── Reporting ─────────────────────────────────────────────────────────────────

ROLE_COLORS = {
    "user":       "\033[94m",   # blue
    "assistant":  "\033[92m",   # green
    "system":     "\033[93m",   # yellow
}
RESET = "\033[0m"
BOLD  = "\033[1m"


def role_label(role: str, width: int = 30) -> str:
    color = ROLE_COLORS.get(role.split("(")[0], "\033[95m")  # magenta for tools
    return f"{color}{role:<{width}}{RESET}"


# ── Agent stats helpers ───────────────────────────────────────────────────────

def _extract_agent_name(role: str):
    """Return (agent_name, direction) or None if not a tool role."""
    if role.startswith("tool_call(") and role.endswith(")"):
        return role[10:-1], "call"
    if role.startswith("tool_result(") and role.endswith(")"):
        return role[12:-1], "result"
    return None


def _agent_stats(turns: list[dict]) -> dict:
    """
    Aggregate per-agent token usage.
    Returns dict keyed by agent name with keys:
      calls, call_tokens, result_tokens, total_tokens, by_turn
    """
    agents: dict[str, dict] = {}
    for t in turns:
        parsed = _extract_agent_name(t["role"])
        if parsed is None:
            continue
        name, direction = parsed
        if name not in agents:
            agents[name] = {
                "calls": 0,
                "call_tokens": 0,
                "result_tokens": 0,
                "total_tokens": 0,
                "by_turn": {},
                "by_model": {},
                "max_call_tokens": 0,
            }
        a = agents[name]
        turn = t["turn"]
        a["by_turn"].setdefault(turn, {"call": 0, "result": 0})
        if direction == "call":
            a["calls"] += 1
            a["call_tokens"] += t["tokens"]
            a["by_turn"][turn]["call"] += t["tokens"]
            if t["tokens"] > a["max_call_tokens"]:
                a["max_call_tokens"] = t["tokens"]
        else:
            a["result_tokens"] += t["tokens"]
            a["by_turn"][turn]["result"] += t["tokens"]
        a["total_tokens"] += t["tokens"]
        m = t.get("model") or "unknown"
        a["by_model"][m] = a["by_model"].get(m, 0) + t["tokens"]
    return agents


def _short_model(m: str, maxlen: int = 22) -> str:
    """Abbreviate a model name for display in narrow columns."""
    m = m.replace("copilot/", "cpl/")
    if len(m) > maxlen:
        m = m[:maxlen - 1] + "…"
    return m


def print_agent_report(agents: dict, turns: list[dict], per_turn: bool = True):
    """Print per-agent breakdown table and orchestrator violation warnings."""
    if not agents:
        return

    total_agent_tokens = sum(a["total_tokens"] for a in agents.values())

    # Aggregate per-model totals across all agent entries
    agent_model_totals: dict[str, int] = {}
    for a in agents.values():
        for m, tok in a.get("by_model", {}).items():
            agent_model_totals[m] = agent_model_totals.get(m, 0) + tok
    multi_model = len(agent_model_totals) > 1

    if multi_model:
        print(f"\n{BOLD}Per-agent breakdown:{RESET}  ({total_agent_tokens:,} agent tokens total)")
        print(f"  {'Agent':<32} {'Calls':>6} {'→ In':>8} {'← Out':>8} {'Total':>8} {'Avg/call':>9} {'Max/call':>9}  {'Model':<22}")
        print(f"  {'─'*32} {'─'*6} {'─'*8} {'─'*8} {'─'*8} {'─'*9} {'─'*9}  {'─'*22}")
    else:
        print(f"\n{BOLD}Per-agent breakdown:{RESET}  ({total_agent_tokens:,} agent tokens total)")
        print(f"  {'Agent':<32} {'Calls':>6} {'→ In':>8} {'← Out':>8} {'Total':>8} {'Avg/call':>9} {'Max/call':>9}")
        print(f"  {'─'*32} {'─'*6} {'─'*8} {'─'*8} {'─'*8} {'─'*9} {'─'*9}")

    for name, a in sorted(agents.items(), key=lambda x: -x[1]["total_tokens"]):
        avg = a["call_tokens"] // a["calls"] if a["calls"] else 0
        if multi_model:
            primary = max(a["by_model"], key=a["by_model"].get) if a.get("by_model") else "unknown"
            print(
                f"  {name:<32} {a['calls']:>6} "
                f"{a['call_tokens']:>8,} {a['result_tokens']:>8,} "
                f"{a['total_tokens']:>8,} {avg:>9,} {a.get('max_call_tokens', 0):>9,}  {_short_model(primary):<22}"
            )
        else:
            print(
                f"  {name:<32} {a['calls']:>6} "
                f"{a['call_tokens']:>8,} {a['result_tokens']:>8,} "
                f"{a['total_tokens']:>8,} {avg:>9,} {a.get('max_call_tokens', 0):>9,}"
            )

    # Totals footer
    total_calls      = sum(a["calls"]        for a in agents.values())
    total_call_tok   = sum(a["call_tokens"]   for a in agents.values())
    total_result_tok = sum(a["result_tokens"] for a in agents.values())
    print(f"  {'─'*32} {'─'*6} {'─'*8} {'─'*8} {'─'*8} {'─'*9} {'─'*9}")
    print(f"  {'  Total':<32} {total_calls:>6} {total_call_tok:>8,} {total_result_tok:>8,} {total_agent_tokens:>8,}")
    if multi_model:
        models_sorted = sorted(agent_model_totals.items(), key=lambda x: -x[1])
        for i, (m, tok) in enumerate(models_sorted):
            branch = "└─" if i == len(models_sorted) - 1 else "├─"
            pct = tok / total_agent_tokens * 100 if total_agent_tokens else 0
            label = f"  {branch} {_short_model(m)}"
            print(f"  {label:<40} {tok:>8,}  ({pct:.1f}%)")

    if per_turn and any(len(a["by_turn"]) > 0 for a in agents.values()):
        print(f"\n{BOLD}Per-agent per-turn cost:  (→ in / ← out){RESET}")
        print(f"  {'Agent':<32} {'Turn-by-turn breakdown'}")
        print(f"  {'─'*32} {'─'*38}")
        for name, a in sorted(agents.items(), key=lambda x: -x[1]["total_tokens"]):
            turns_sorted = sorted(a["by_turn"].items())
            turn_strs = [
                f"T{t}(→{v['call']:,}/←{v['result']:,})"
                for t, v in turns_sorted
            ]
            display = name.replace("[root~]/", "[root]/")
            line = " | ".join(turn_strs)
            print(f"  {display:<32} {line}")

    # ── Orchestrator constraint violations ──────────────────────────────────
    # [root~]/ entries = confirmed violations: ARTHUR called execution_subagent
    #   directly in the same response, so there was no delegation context.
    # [root]/  entries = possible violations: no execution_subagent in context —
    #   may be a legitimate VS Code tagging gap rather than a direct ARTHUR call.
    WARN  = "\033[93m"  # yellow
    ERR   = "\033[91m"  # red
    confirmed_violations: list[tuple] = []
    possible_violations:  list[tuple] = []
    for name in agents:
        a = agents[name]
        primary_model = max(a["by_model"], key=a["by_model"].get) if a.get("by_model") else "unknown"
        if name.startswith("[root~]/"):
            tool_name = name[len("[root~]/"):]
            if tool_name in ARTHUR_FORBIDDEN_TOOLS:
                confirmed_violations.append((name, a["calls"], a["call_tokens"], a["result_tokens"], a["total_tokens"], primary_model, a.get("max_call_tokens", 0)))
        elif name.startswith("[root]/"):
            tool_name = name[len("[root]/"):]
            if tool_name in ARTHUR_FORBIDDEN_TOOLS:
                possible_violations.append((name, a["calls"], a["call_tokens"], a["result_tokens"], a["total_tokens"], primary_model, a.get("max_call_tokens", 0)))

    VIO_COL = 32  # tool name column width in violation tables
    if confirmed_violations:
        print(f"\n{ERR}{BOLD}✗  Confirmed orchestrator constraint violations:{RESET}")
        print(f"  ARTHUR called forbidden tools with no delegation context in scope:")
        if multi_model:
            print(f"  {'Tool':<{VIO_COL}} {'Calls':>6} {'→ In':>8} {'← Out':>8} {'Total':>8} {'Avg/call':>9} {'Max/call':>9}  {'Model':<22}")
            print(f"  {'─'*VIO_COL} {'─'*6} {'─'*8} {'─'*8} {'─'*8} {'─'*9} {'─'*9}  {'─'*22}")
        else:
            print(f"  {'Tool':<{VIO_COL}} {'Calls':>6} {'→ In':>8} {'← Out':>8} {'Total':>8} {'Avg/call':>9} {'Max/call':>9}")
            print(f"  {'─'*VIO_COL} {'─'*6} {'─'*8} {'─'*8} {'─'*8} {'─'*9} {'─'*9}")
        for name, calls, in_tok, out_tok, total, model, max_call in sorted(confirmed_violations, key=lambda x: -x[4]):
            avg = in_tok // calls if calls else 0
            if multi_model:
                print(f"  {ERR}{name:<{VIO_COL}}{RESET} {calls:>6} {in_tok:>8,} {out_tok:>8,} {total:>8,} {avg:>9,} {max_call:>9,}  {_short_model(model):<22}")
            else:
                print(f"  {ERR}{name:<{VIO_COL}}{RESET} {calls:>6} {in_tok:>8,} {out_tok:>8,} {total:>8,} {avg:>9,} {max_call:>9,}")
        total_cv_calls  = sum(x[1] for x in confirmed_violations)
        total_cv_in     = sum(x[2] for x in confirmed_violations)
        total_cv_out    = sum(x[3] for x in confirmed_violations)
        total_cv_tokens = sum(x[4] for x in confirmed_violations)
        print(f"  {'─'*VIO_COL} {'─'*6} {'─'*8} {'─'*8} {'─'*8} {'─'*9} {'─'*9}")
        print(f"  {ERR}{'  Total':<{VIO_COL}}{RESET} {total_cv_calls:>6} {total_cv_in:>8,} {total_cv_out:>8,} {total_cv_tokens:>8,}")
    if possible_violations:
        print(f"\n{WARN}{BOLD}⚠  Possible orchestrator constraint violations:{RESET}")
        print(f"  Root-level calls to forbidden tools — could be VS Code tagging gaps:")
        if multi_model:
            print(f"  {'Tool':<{VIO_COL}} {'Calls':>6} {'→ In':>8} {'← Out':>8} {'Total':>8} {'Avg/call':>9} {'Max/call':>9}  {'Model':<22}")
            print(f"  {'─'*VIO_COL} {'─'*6} {'─'*8} {'─'*8} {'─'*8} {'─'*9} {'─'*9}  {'─'*22}")
        else:
            print(f"  {'Tool':<{VIO_COL}} {'Calls':>6} {'→ In':>8} {'← Out':>8} {'Total':>8} {'Avg/call':>9} {'Max/call':>9}")
            print(f"  {'─'*VIO_COL} {'─'*6} {'─'*8} {'─'*8} {'─'*8} {'─'*9} {'─'*9}")
        for name, calls, in_tok, out_tok, total, model, max_call in sorted(possible_violations, key=lambda x: -x[4]):
            avg = in_tok // calls if calls else 0
            if multi_model:
                print(f"  {WARN}{name:<{VIO_COL}}{RESET} {calls:>6} {in_tok:>8,} {out_tok:>8,} {total:>8,} {avg:>9,} {max_call:>9,}  {_short_model(model):<22}")
            else:
                print(f"  {WARN}{name:<{VIO_COL}}{RESET} {calls:>6} {in_tok:>8,} {out_tok:>8,} {total:>8,} {avg:>9,} {max_call:>9,}")
    if not confirmed_violations and not possible_violations:
        root_tools = [n for n in agents if n.startswith("[root~]/") or n.startswith("[root]/")]
        if root_tools:
            print(f"\n\033[92m\u2713  No orchestrator constraint violations detected.{RESET}")

    # ── Orchestrator direct footprint ───────────────────────────────────
    # Reconciles the orchestrator's model total: assistant prose + user messages +
    # legitimate root tools + violations = total orchestrator model tokens.
    assistant_tokens = sum(t["tokens"] for t in turns if t["role"] == "assistant")
    user_tokens      = sum(t["tokens"] for t in turns if t["role"] in ("user", "system"))

    orch_model = next(
        (t["model"] for t in turns if t["role"] == "assistant" and t["model"] != "unknown"),
        "unknown",
    )

    # Collapse [root]/foo and [root~]/foo into a single entry per tool name.
    legit_root_by_tool: dict[str, list] = {}
    for name, a in agents.items():
        if name.startswith("[root~]/"):
            tool_name = name[len("[root~]/"):]
        elif name.startswith("[root]/"):
            tool_name = name[len("[root]/"):]
        else:
            continue
        if tool_name not in ARTHUR_FORBIDDEN_TOOLS:
            legit_root_by_tool.setdefault(tool_name, [0, 0])
            legit_root_by_tool[tool_name][0] += a["calls"]
            legit_root_by_tool[tool_name][1] += a["total_tokens"]
    legit_root = [(t, c, tok) for t, (c, tok) in legit_root_by_tool.items()]

    legit_total     = sum(t for _, _, t in legit_root)
    confirmed_total = sum(x[4] for x in confirmed_violations)
    possible_total  = sum(x[4] for x in possible_violations)
    orch_total      = assistant_tokens + user_tokens + legit_total + confirmed_total + possible_total

    GREEN = "\033[92m"
    print(f"\n{BOLD}Orchestrator direct footprint:{RESET}  ({orch_model})")
    print(f"  {'─'*52}")
    print(f"  {'Category':<38} {'Tokens':>8}")
    print(f"  {'─'*38} {'─'*8}")
    print(f"  {'Orchestrator assistant (thinking + prose)':<38} {assistant_tokens:>8,}")
    print(f"  {'User messages':<38} {user_tokens:>8,}")
    if legit_root:
        parts = ", ".join(
            f"{tool}×{c}"
            for tool, c, _ in sorted(legit_root, key=lambda x: -x[2])
        )
        suffix = (parts[:48] + "…") if len(parts) > 48 else parts
        print(f"  {'Legitimate root tools':<38} {legit_total:>8,}  {suffix}")
    print(f"  {'─'*38} {'─'*8}")
    legit_subtotal = assistant_tokens + user_tokens + legit_total
    print(f"  {GREEN}{'  Subtotal: legitimate':<38}{RESET} {legit_subtotal:>8,}")
    if confirmed_total:
        v_parts = ", ".join(
            f"{n.replace('[root~]/', '')}\u00d7{c}"
            for n, c, _i, _o, _t, _m, _mx in sorted(confirmed_violations, key=lambda x: -x[4])
        )
        v_suffix = (v_parts[:48] + "…") if len(v_parts) > 48 else v_parts
        print(f"  {ERR}{'  Confirmed violations':<38}{RESET} {confirmed_total:>8,}  {v_suffix}")
    if possible_total:
        print(f"  {WARN}{'  Possible violations':<38}{RESET} {possible_total:>8,}")
    print(f"  {'─'*38} {'─'*8}")
    print(f"  {BOLD}{'  Total orchestrator tokens':<38}{RESET} {orch_total:>8,}")


def _tool_type_stats(turns: list[dict]) -> dict:
    stats: dict[str, dict] = {}
    for t in turns:
        role = t["role"]
        if role.startswith("tool_call(") and role.endswith(")"):
            inner = role[10:-1]
            direction = "call"
        elif role.startswith("tool_result(") and role.endswith(")"):
            inner = role[12:-1]
            direction = "result"
        else:
            continue
        if "/" in inner:
            base = inner.rsplit("/", 1)[1]
        else:
            base = inner
        if base not in stats:
            stats[base] = {"calls": 0, "call_tokens": 0, "result_tokens": 0, "total_tokens": 0, "max_call_tokens": 0}
        s = stats[base]
        if direction == "call":
            s["calls"] += 1
            s["call_tokens"] += t["tokens"]
            if t["tokens"] > s["max_call_tokens"]:
                s["max_call_tokens"] = t["tokens"]
        else:
            s["result_tokens"] += t["tokens"]
        s["total_tokens"] += t["tokens"]
    return stats


def print_tool_type_report(tool_stats: dict):
    if not tool_stats:
        return
    total_calls      = sum(s["calls"]         for s in tool_stats.values())
    total_call_tok   = sum(s["call_tokens"]   for s in tool_stats.values())
    total_result_tok = sum(s["result_tokens"] for s in tool_stats.values())
    total_tokens     = sum(s["total_tokens"]  for s in tool_stats.values())
    print(f"\n{BOLD}Tool type breakdown:{RESET}  ({len(tool_stats)} unique tools)")
    print(f"  {'Tool':<32} {'Calls':>6}  {'→ In':>6} {'← Out':>8} {'Total':>8} {'Avg/call':>9} {'Max/call':>9}")
    print(f"  {'─'*32} {'─'*6}  {'─'*6} {'─'*8} {'─'*8} {'─'*9} {'─'*9}")
    for name, s in sorted(tool_stats.items(), key=lambda x: -x[1]["total_tokens"]):
        avg = s["call_tokens"] // s["calls"] if s["calls"] else 0
        print(f"  {name:<32} {s['calls']:>6}  {s['call_tokens']:>6,} {s['result_tokens']:>8,} {s['total_tokens']:>8,} {avg:>9,} {s.get('max_call_tokens', 0):>9,}")
    print(f"  {'─'*32} {'─'*6}  {'─'*6} {'─'*8} {'─'*8} {'─'*9} {'─'*9}")
    print(f"  {'  Total':<32} {total_calls:>6}  {total_call_tok:>6,} {total_result_tok:>8,} {total_tokens:>8,}")


def print_session_report(path, turns: list[dict], summary_only: bool = False, top_n: int = 0):
    if not turns:
        return

    total_in  = sum(t["tokens"] for t in turns if t["role"] in ("user", "system") or t["role"].startswith("tool_call("))
    total_out = sum(t["tokens"] for t in turns if t["role"] == "assistant" or t["role"].startswith("tool_result("))
    total     = sum(t["tokens"] for t in turns)

    models = sorted({t["model"] for t in turns if t["model"] != "unknown"})
    model_str = ", ".join(models) if models else "unknown"

    print(f"\n{'='*72}")
    print(f"{BOLD}File   :{RESET} {path.name}")
    print(f"{BOLD}Path   :{RESET} {path}")
    print(f"{BOLD}Models :{RESET} {model_str}")
    print(f"{BOLD}Turns  :{RESET} {max(t['turn'] for t in turns)}")
    print(f"{BOLD}Tokens :{RESET} {total:,}  (in ≈ {total_in:,} / out ≈ {total_out:,})")
    print(f"{'─'*72}")

    if not summary_only:
        display_turns = sorted(turns, key=lambda t: -t["tokens"])[:top_n] if top_n > 0 else turns
        display_turns = sorted(display_turns, key=lambda t: (t["turn"], turns.index(t)))
        if top_n > 0 and len(display_turns) < len(turns):
            print(f"  (showing top {top_n} of {len(turns)} entries by tokens)")
        print(f"{'Turn':<6} {'Role':<32} {'Tokens':>8} {'%Tot':>6}  {'Preview'}")
        print(f"{'─'*72}")
        for t in display_turns:
            pct = t["tokens"] / total * 100 if total else 0
            preview = t["content"].replace("\n", " ")[:55]
            if len(t["content"]) > 55:
                preview += "…"
            print(f"{t['turn']:<6} {role_label(t['role'], 32)} {t['tokens']:>8,} {pct:>5.1f}%  {preview}")
        print(f"{'─'*72}")
        if len(turns) >= 6:
            top5 = sorted(turns, key=lambda t: -t["tokens"])[:5]
            print(f"\nTop 5 most expensive entries:")
            print(f"  {'Rank':<4}  {'Turn':<6}  {'Role':<32}  {'Tokens':>6}  {'%Tot':>5}")
            print(f"  {'─'*4}  {'─'*6}  {'─'*32}  {'─'*6}  {'─'*5}")
            for i, t in enumerate(top5, 1):
                pct = t["tokens"] / total * 100 if total else 0
                print(f"  #{i:<3}  {t['turn']:<6}  {t['role']:<32}  {t['tokens']:>6,}  {pct:>4.1f}%")

    # Per-agent breakdown
    agents = _agent_stats(turns)
    print_agent_report(agents, turns, per_turn=not summary_only)
    print_tool_type_report(_tool_type_stats(turns))

    # Per-model breakdown (per-session)
    model_totals: dict[str, int] = {}
    for t in turns:
        m = t["model"] or "unknown"
        model_totals[m] = model_totals.get(m, 0) + t["tokens"]

    if len(model_totals) > 1:
        print(f"\n{BOLD}Per-model breakdown:{RESET}")
        for m, tok in sorted(model_totals.items(), key=lambda x: -x[1]):
            print(f"  {m:<35} {tok:>10,} tokens")

def print_grand_total(all_turns: list[dict]):
    if not all_turns:
        print("\nNo Copilot session data found.")
        return

    total     = sum(t["tokens"] for t in all_turns)
    total_in  = sum(t["tokens"] for t in all_turns if t["role"] in ("user", "system") or t["role"].startswith("tool_call("))
    total_out = sum(t["tokens"] for t in all_turns if t["role"] == "assistant" or t["role"].startswith("tool_result("))

    model_totals: dict[str, int] = {}
    for t in all_turns:
        m = t["model"] or "unknown"
        model_totals[m] = model_totals.get(m, 0) + t["tokens"]

    print(f"\n{'='*72}")
    print(f"{BOLD}GRAND TOTAL ACROSS ALL SESSIONS{RESET}")
    print(f"{'='*72}")
    print(f"  Total tokens   : {total:>12,}")
    print(f"  Input  (≈)     : {total_in:>12,}")
    print(f"  Output (≈)     : {total_out:>12,}")
    print(f"\n  Per-model breakdown:")
    for m, tok in sorted(model_totals.items(), key=lambda x: -x[1]):
        pct = tok / total * 100 if total else 0
        bar = "█" * int(pct / 2.5)
        print(f"    {m:<35} {tok:>10,}  ({pct:4.1f}%)  {bar}")
    print(f"\n{'='*72}")

    if not TIKTOKEN_AVAILABLE:
        print("  ℹ  Estimates only — install tiktoken for accurate counts:")
        print("       pip install tiktoken")


# ── Compare report ────────────────────────────────────────────────────────────

def _session_stats(turns: list[dict]) -> dict:
    """Compute summary stats dict from a list of turns."""
    total     = sum(t["tokens"] for t in turns)
    total_in  = sum(t["tokens"] for t in turns if t["role"] in ("user", "system") or t["role"].startswith("tool_call("))
    total_out = sum(t["tokens"] for t in turns if t["role"] == "assistant" or t["role"].startswith("tool_result("))
    n_turns   = max((t["turn"] for t in turns), default=0)

    model_totals: dict[str, int] = {}
    for t in turns:
        m = t["model"] or "unknown"
        model_totals[m] = model_totals.get(m, 0) + t["tokens"]

    role_totals: dict[str, int] = {}
    for t in turns:
        r = t["role"]
        role_totals[r] = role_totals.get(r, 0) + t["tokens"]

    return {
        "total": total,
        "input": total_in,
        "output": total_out,
        "turns": n_turns,
        "by_model": model_totals,
        "by_role": role_totals,
        "turn_list": turns,
    }


def _delta_str(baseline: int, optimized: int, width: int = 0) -> str:
    """Format an absolute + percentage delta, coloured green (savings) or red (increase)."""
    diff = optimized - baseline
    pct  = (diff / baseline * 100) if baseline else 0.0
    sign = "+" if diff > 0 else ""
    color = "\033[91m" if diff > 0 else ("\033[92m" if diff < 0 else "\033[0m")
    text = f"{sign}{diff:,}  ({sign}{pct:.1f}%)"
    if width:
        text = f"{text:>{width}}"
    return f"{color}{text}\033[0m"


def _bar(value: int, maximum: int, width: int = 30) -> str:
    filled = min(width, int(value / maximum * width)) if maximum else 0
    return "█" * filled + "░" * (width - filled)


def print_compare_report(
    baseline_path: Path, baseline_turns: list[dict],
    optimized_path: Path, optimized_turns: list[dict],
):
    b = _session_stats(baseline_turns)
    o = _session_stats(optimized_turns)

    W = 72
    print(f"\n{'='*W}")
    print(f"{BOLD}COMPARISON REPORT{RESET}")
    print(f"{'='*W}")
    print(f"  {'Baseline :':<12} {baseline_path.name}")
    print(f"  {'Optimized:':<12} {optimized_path.name}")
    print(f"{'─'*W}")

    # ── Top-level summary table ──
    col = 16
    print(f"\n  {'Metric':<22} {'Baseline':>{col}} {'Optimized':>{col}}  {'Delta':>22}")
    print(f"  {'─'*22} {'─'*col} {'─'*col}  {'─'*22}")

    rows = [
        ("Total tokens",   b["total"],  o["total"]),
        ("  Input  (≈)",   b["input"],  o["input"]),
        ("  Output (≈)",   b["output"], o["output"]),
        ("Turns",          b["turns"],  o["turns"]),
    ]
    for label, bv, ov in rows:
        print(f"  {label:<22} {bv:>{col},} {ov:>{col},}  {_delta_str(bv, ov, width=22)}")

    # ── Visual token bar comparison ──
    max_total = max(b["total"], o["total"], 1)
    print(f"\n  {'Token volume':}")
    print(f"  Baseline  [{_bar(b['total'], max_total)}] {b['total']:,}")
    print(f"  Optimized [{_bar(o['total'], max_total)}] {o['total']:,}")

    # ── Input vs output split ──
    print(f"\n  {'Input / Output split':}")
    for label, stats in [("Baseline ", b), ("Optimized", o)]:
        total = stats["total"] or 1
        in_pct  = stats["input"]  / total * 100
        out_pct = stats["output"] / total * 100
        in_bar  = "▓" * int(in_pct  / 2.5)
        out_bar = "░" * int(out_pct / 2.5)
        print(f"  {label}  IN [{in_bar:<40}] {in_pct:.0f}%"
              f"   OUT [{out_bar:<40}] {out_pct:.0f}%")

    # ── Per-role breakdown ──
    all_roles = sorted(set(b["by_role"]) | set(o["by_role"]))
    if all_roles:
        print(f"\n  {'Per-role breakdown':}")
        print(f"  {'Role':<32} {'Baseline':>10} {'Optimized':>10}  {'Delta':>20}")
        print(f"  {'─'*32} {'─'*10} {'─'*10}  {'─'*20}")
        for role in all_roles:
            bv = b["by_role"].get(role, 0)
            ov = o["by_role"].get(role, 0)
            print(f"  {role:<32} {bv:>10,} {ov:>10,}  {_delta_str(bv, ov)}")

    # ── Per-model breakdown ──
    all_models = sorted(set(b["by_model"]) | set(o["by_model"]))
    if len(all_models) > 0:
        print(f"\n  {'Per-model breakdown':}")
        print(f"  {'Model':<35} {'Baseline':>10} {'Optimized':>10}  {'Delta':>20}")
        print(f"  {'─'*35} {'─'*10} {'─'*10}  {'─'*20}")
        for model in all_models:
            bv = b["by_model"].get(model, 0)
            ov = o["by_model"].get(model, 0)
            print(f"  {model:<35} {bv:>10,} {ov:>10,}  {_delta_str(bv, ov)}")

    # ── Per-turn comparison (if turn counts match) ──
    b_turns = b["turn_list"]
    o_turns = o["turn_list"]

    b_by_turn: dict[tuple, list] = {}
    for t in b_turns:
        key = (t["turn"], t["role"])
        b_by_turn.setdefault(key, []).append(t)

    o_by_turn: dict[tuple, list] = {}
    for t in o_turns:
        key = (t["turn"], t["role"])
        o_by_turn.setdefault(key, []).append(t)

    all_keys = sorted(set(b_by_turn) | set(o_by_turn))

    if all_keys:
        print(f"\n  {'Per-turn comparison':}")
        print(f"  {'Turn':<6} {'Role':<30} {'Baseline':>10} {'Optimized':>10}  {'Delta':>20}")
        print(f"  {'─'*6} {'─'*30} {'─'*10} {'─'*10}  {'─'*20}")
        for key in all_keys:
            turn_num, role = key
            bv = sum(t["tokens"] for t in b_by_turn.get(key, []))
            ov = sum(t["tokens"] for t in o_by_turn.get(key, []))
            only = " ← baseline only" if ov == 0 else (" ← new" if bv == 0 else "")
            print(f"  {turn_num:<6} {role:<30} {bv:>10,} {ov:>10,}  {_delta_str(bv, ov)}{only}")

    # ── Net savings summary ──
    saved       = b["total"]  - o["total"]
    saved_in    = b["input"]  - o["input"]
    saved_out   = b["output"] - o["output"]
    saved_pct   = saved / b["total"] * 100 if b["total"] else 0

    print(f"\n{'─'*W}")
    print(f"{BOLD}  NET SAVINGS{RESET}")
    direction = "saved" if saved >= 0 else "added"
    color     = "\033[92m" if saved >= 0 else "\033[91m"
    print(f"  Total  : {color}{abs(saved):,} tokens {direction}  ({abs(saved_pct):.1f}%)\033[0m")
    print(f"  Input  : {_delta_str(b['input'],  o['input'])}")
    print(f"  Output : {_delta_str(b['output'], o['output'])}")
    print(f"{'='*W}")

    if not TIKTOKEN_AVAILABLE:
        print("  ℹ  Estimates only — install tiktoken for accurate counts:")
        print("       pip install tiktoken")


# ── Markdown writer ──────────────────────────────────────────────────────────

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _write_markdown(md_path: Path, report_text: str) -> None:
    """Write *report_text* (plain text, ANSI stripped) as a Markdown code block."""
    clean = _strip_ansi(report_text)
    md_path.write_text(
        f"```\n{clean}\n```\n",
        encoding="utf-8",
    )
    print(f"  ✓  Markdown report written to: {md_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Analyze GitHub Copilot Chat token usage from session logs."
    )
    parser.add_argument("--file",    help="Parse a single session file")
    parser.add_argument("--dir",     help="Scan all .json/.jsonl files in a directory")
    parser.add_argument("--summary", action="store_true",
                        help="Show only summary per file, not per-turn detail")
    parser.add_argument("--days",    type=int, default=0,
                        help="Only include files modified in the last N days (0 = all)")
    parser.add_argument("--compare", nargs=2, metavar=("BASELINE", "OPTIMIZED"),
                        help="Compare two exported chat JSON files and show delta")
    parser.add_argument("--md", action="store_true", default=None,
                        help="Write a Markdown report alongside the source file(s) "
                             "(named <source>_tokens.md). Default: on for --file, off for --dir/auto")
    parser.add_argument("--no-md", action="store_true",
                        help="Suppress Markdown output even when --file is used")
    parser.add_argument("--top", type=int, default=0, metavar="N",
                        help="In the detail table, show only the N most expensive rows (0 = all)")
    args = parser.parse_args()

    # --file mode: write markdown by default unless --no-md is set
    if args.file and not args.no_md and args.md is None:
        args.md = True
    elif args.md is None:
        args.md = False

    # ── Compare mode ──
    if args.compare:
        baseline_path  = Path(args.compare[0])
        optimized_path = Path(args.compare[1])

        print(f"📂 Parsing baseline  : {baseline_path.name}")
        baseline_turns = parse_file(baseline_path)
        if not baseline_turns:
            print(f"  ✗ No turns found in baseline file: {baseline_path}")
            sys.exit(1)

        print(f"📂 Parsing optimized : {optimized_path.name}")
        optimized_turns = parse_file(optimized_path)
        if not optimized_turns:
            print(f"  ✗ No turns found in optimized file: {optimized_path}")
            sys.exit(1)

        if args.md:
            buf = io.StringIO()
            with redirect_stdout(buf):
                print_compare_report(baseline_path, baseline_turns, optimized_path, optimized_turns)
            report_text = buf.getvalue()
            print(report_text, end="")
            md_path = optimized_path.parent / f"{optimized_path.stem}_tokens.md"
            _write_markdown(md_path, report_text)
        else:
            print_compare_report(baseline_path, baseline_turns, optimized_path, optimized_turns)
        return

    cutoff = None
    if args.days > 0:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=args.days)

    # ── Collect files ──
    if args.file:
        files = [Path(args.file)]
    elif args.dir:
        scan = Path(args.dir)
        files = list(scan.rglob("*.json")) + list(scan.rglob("*.jsonl"))
    else:
        print("🔍 Auto-discovering Copilot session files …")
        vscode_paths = get_vscode_paths()
        if not vscode_paths:
            print("  ✗ No VS Code user-data directories found.")
            print("  Try: python copilot_token_analyzer.py --dir /path/to/chatSessions")
            sys.exit(1)
        print(f"  Found VS Code data in: {', '.join(str(p) for p in vscode_paths)}")
        files = find_session_files(vscode_paths)
        print(f"  Found {len(files)} candidate session file(s)\n")

    if cutoff:
        files = [
            f for f in files
            if datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc) >= cutoff
        ]

    if not files:
        print("No session files found matching your criteria.")
        sys.exit(1)

    # ── Parse and report ──
    all_turns: list[dict] = []
    parsed_count = 0

    for f in sorted(files):
        turns = parse_file(f)
        if not turns:
            continue
        parsed_count += 1
        all_turns += turns

        if args.md:
            buf = io.StringIO()
            with redirect_stdout(buf):
                print_session_report(f, turns, summary_only=args.summary, top_n=args.top)
            session_text = buf.getvalue()
            print(session_text, end="")
            md_path = f.parent / f"{f.stem}_tokens.md"
            _write_markdown(md_path, session_text)
        else:
            print_session_report(f, turns, summary_only=args.summary, top_n=args.top)

    print(f"\n  Parsed {parsed_count} session file(s) with content.")

    if args.md and len(files) > 1:
        # For multi-file runs, write a combined grand-total markdown too
        buf = io.StringIO()
        with redirect_stdout(buf):
            print_grand_total(all_turns)
        grand_text = buf.getvalue()
        print(grand_text, end="")
        # Place combined report next to first file
        first_file = sorted(f for f in files if parse_file(f))[0]
        md_path = first_file.parent / "_grand_total_tokens.md"
        _write_markdown(md_path, grand_text)
    else:
        print_grand_total(all_turns)


if __name__ == "__main__":
    main()
