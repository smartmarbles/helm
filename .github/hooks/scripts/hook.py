#!/usr/bin/env python3
"""Generic Copilot agent hook script.

Handles: SessionStart, UserPromptSubmit, PreToolUse, PostToolUse,
         PreCompact, SubagentStart, SubagentStop, Stop
Logs all events to .agent-memory/session/hook-log.jsonl

Single cross-platform implementation (Windows/macOS/Linux) — replaces the
former hook.sh + hook.ps1 pair. Requires only a Python 3 interpreter on PATH.
"""
import glob
import json
import os
import sys
from datetime import datetime, timezone

LOG_DIR = os.path.join(".agent-memory", "session")


def read_stdin_json():
    raw = sys.stdin.read()
    if not raw:
        return raw, None
    try:
        return raw, json.loads(raw)
    except Exception:
        return raw, None


def extract_fields(payload):
    hook_event = "unknown"
    agent_name = "unknown"
    tool_name = ""
    if isinstance(payload, dict):
        hook_event = payload.get("hook_event_name") or payload.get("hookEventName") or "unknown"
        for k in ("agent_type", "agentName", "agent_name", "agent"):
            if payload.get(k):
                agent_name = str(payload[k])
                break
        tool_name = payload.get("tool_name") or ""
        # For PreToolUse/runSubagent, agentName may be nested inside tool_input
        if agent_name == "unknown":
            tool_input = payload.get("tool_input") or {}
            if isinstance(tool_input, dict):
                for k in ("agentName", "agent_name", "agent_type", "agent"):
                    if tool_input.get(k):
                        agent_name = str(tool_input[k])
                        break
    return hook_event, agent_name, tool_name


def load_state(state_file):
    state = {"current": "ARTHUR", "stack": []}
    if os.path.exists(state_file):
        try:
            with open(state_file, encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            pass
    return state


def save_state(state_file, state):
    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, separators=(",", ":"))
    except Exception:
        pass


def emit(obj):
    print(json.dumps(obj))


def main():
    raw, payload = read_stdin_json()
    hook_event, agent_name, tool_name = extract_fields(payload)

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    os.makedirs(LOG_DIR, exist_ok=True)
    state_file = os.path.join(LOG_DIR, "agent-state.json")

    state = load_state(state_file)
    tracked = state.get("current", "ARTHUR")
    if agent_name == "unknown":
        agent_name = tracked

    if hook_event == "SessionStart":
        save_state(state_file, {"current": "ARTHUR", "stack": []})
    elif hook_event == "SubagentStart" and agent_name != "unknown":
        stack = list(state.get("stack", []))
        stack.append(tracked)
        save_state(state_file, {"current": agent_name, "stack": stack})
    elif hook_event == "SubagentStop":
        stack = list(state.get("stack", []))
        if stack:
            parent = stack.pop()
        else:
            parent = "ARTHUR"
        save_state(state_file, {"current": parent, "stack": stack})

    log_entry = {"event": hook_event, "agent": agent_name, "tool": tool_name, "timestamp": now_iso}
    if payload is not None:
        log_entry["payload"] = payload
    try:
        with open(os.path.join(LOG_DIR, "hook-log.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass

    # --- SubagentStart: look up and inject session checkpoint ---
    if hook_event == "SubagentStart":
        if agent_name != "unknown" and agent_name:
            slug = agent_name.lower()
            candidates = glob.glob(os.path.join(LOG_DIR, f"{slug}-*.md"))
            checkpoint_file = max(candidates, key=os.path.getmtime) if candidates else None
            if checkpoint_file:
                with open(checkpoint_file, encoding="utf-8") as f:
                    checkpoint_content = f.read().strip()
                system_message = (
                    f"[SubagentStart] Current UTC time: {now_utc}\n\n"
                    f"A prior session checkpoint was found for agent '{agent_name}'. Resume from it:\n\n"
                    f"{checkpoint_content}"
                )
            else:
                system_message = (
                    f"[SubagentStart] Current UTC time: {now_utc}\n\n"
                    "No prior session checkpoint found. Follow the Session Resumption Protocol "
                    "(AGENTS.md): check /memories/session/ and /memories/repo/ before beginning work."
                )
        else:
            system_message = f"[SubagentStart] Current UTC time: {now_utc}"
        emit({"systemMessage": system_message})
        return

    # --- SessionStart: inject UTC time + resumption protocol reminder ---
    if hook_event == "SessionStart":
        workspace = "unknown"
        session_id = "unknown"
        if isinstance(payload, dict):
            cwd = (payload.get("cwd") or "").replace("\\", "/").rstrip("/")
            workspace = cwd.rsplit("/", 1)[-1] if cwd else "unknown"
            session_id = payload.get("session_id") or "unknown"

        border = "#" * 54
        blank = "#  " + (" " * 48) + "  #"
        banner = "\n".join([
            border, blank,
            "#  {:<48}  #".format("SESSION START"),
            "#  {:<48}  #".format(f"Workspace : {workspace}"),
            "#  {:<48}  #".format(f"Session   : {session_id}"),
            "#  {:<48}  #".format(f"Time      : {now_utc}"),
            blank, border,
        ])
        print(banner, file=sys.stderr)

        system_message = (
            f"[SessionStart] Current UTC time: {now_utc}\n\n"
            "Follow the Session Resumption Protocol (AGENTS.md): check /memories/session/ and "
            "/memories/repo/ before beginning work."
        )
        emit({"systemMessage": system_message})
        return

    # --- All other hooks: log-only, pass through ---
    print("{}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never block the agent on a hook failure.
        print("{}")
