#!/usr/bin/env bash
# Generic Copilot agent hook script
# Handles: SessionStart, UserPromptSubmit, PreToolUse, PostToolUse,
#          PreCompact, SubagentStart, SubagentStop, Stop
# Logs all events to .agent-memory/session/hook-log.jsonl

set -euo pipefail

# --- Read stdin ---
raw=$(cat)

hook_event="unknown"
agent_name="unknown"
tool_name=""

if [ -n "$raw" ] && command -v python3 &>/dev/null; then
    _parsed=$(echo "$raw" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    event = data.get('hook_event_name', data.get('hookEventName', 'unknown'))
    agent = 'unknown'
    for k in ('agent_type', 'agentName', 'agent_name', 'agent'):
        if k in data and data[k]:
            agent = str(data[k])
            break
    tool = data.get('tool_name', '') or ''
    # For PreToolUse/runSubagent, agentName may be nested inside tool_input
    if agent == 'unknown':
        ti = data.get('tool_input') or {}
        for k in ('agentName', 'agent_name', 'agent_type', 'agent'):
            if k in ti and ti[k]:
                agent = str(ti[k])
                break
    print(event)
    print(agent)
    print(tool)
except Exception:
    print('unknown')
    print('unknown')
    print('')
" 2>/dev/null || printf 'unknown\nunknown\n')
    hook_event=$(echo "$_parsed" | sed -n '1p')
    agent_name=$(echo "$_parsed" | sed -n '2p')
    tool_name=$(echo "$_parsed" | sed -n '3p')
fi

now_utc=$(date -u "+%Y-%m-%d %H:%M:%S UTC")
now_iso=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

# --- Write audit log ---
log_dir=".agent-memory/session"
mkdir -p "$log_dir"

# --- Agent state tracking ---
_resolved_agent=$(python3 - "$log_dir/agent-state.json" "$hook_event" "$agent_name" <<'PYEOF'
import json, sys, os

state_file = sys.argv[1]
hook_event = sys.argv[2]
agent_name = sys.argv[3]

state = {"current": "ARTHUR", "stack": []}
if os.path.exists(state_file):
    try:
        with open(state_file) as f:
            state = json.load(f)
    except Exception:
        pass

tracked = state.get("current", "ARTHUR")
if agent_name == "unknown":
    agent_name = tracked

if hook_event == "SessionStart":
    new_state = {"current": "ARTHUR", "stack": []}
    with open(state_file, "w") as f:
        json.dump(new_state, f, separators=(",", ":"))
elif hook_event == "SubagentStart" and agent_name != "unknown":
    stack = list(state.get("stack", []))
    stack.append(tracked)
    new_state = {"current": agent_name, "stack": stack}
    with open(state_file, "w") as f:
        json.dump(new_state, f, separators=(",", ":"))
elif hook_event == "SubagentStop":
    stack = list(state.get("stack", []))
    if stack:
        parent = stack[-1]
        new_stack = stack[:-1]
    else:
        parent = "ARTHUR"
        new_stack = []
    new_state = {"current": parent, "stack": new_stack}
    with open(state_file, "w") as f:
        json.dump(new_state, f, separators=(",", ":"))

print(agent_name)
PYEOF
2>/dev/null || echo "$agent_name")
agent_name="$_resolved_agent"

log_entry=$(python3 -c "
import json, sys
try:
    payload = json.loads(sys.argv[1])
except Exception:
    payload = None
entry = {'event': sys.argv[2], 'agent': sys.argv[3], 'tool': sys.argv[4], 'timestamp': sys.argv[5]}
if payload is not None:
    entry['payload'] = payload
print(json.dumps(entry))
" "$raw" "$hook_event" "$agent_name" "$tool_name" "$now_iso" 2>/dev/null \
    || echo "{\"event\":\"$hook_event\",\"agent\":\"$agent_name\",\"timestamp\":\"$now_iso\"}")

echo "$log_entry" >> "$log_dir/hook-log.jsonl"

# --- SubagentStart: look up and inject session checkpoint ---
if [ "$hook_event" = "SubagentStart" ]; then
    if [ "$agent_name" != "unknown" ] && [ -n "$agent_name" ]; then
        slug=$(echo "$agent_name" | tr '[:upper:]' '[:lower:]')
        checkpoint_file=$(ls -t "$log_dir/${slug}-"*.md 2>/dev/null | head -1 || true)
        if [ -n "$checkpoint_file" ] && [ -f "$checkpoint_file" ]; then
            checkpoint_content=$(cat "$checkpoint_file")
            system_message="[SubagentStart] Current UTC time: $now_utc

A prior session checkpoint was found for agent '$agent_name'. Resume from it:

$(echo "$checkpoint_content" | sed 's/[\\]/\\\\/g')"
        else
            system_message="[SubagentStart] Current UTC time: $now_utc

No prior session checkpoint found. Follow the Session Resumption Protocol (AGENTS.md): check /memories/session/ and /memories/repo/ before beginning work."
        fi
    else
        system_message="[SubagentStart] Current UTC time: $now_utc"
    fi
    python3 -c "import json, sys; print(json.dumps({'systemMessage': sys.argv[1]}))" "$system_message"
    exit 0
fi

# --- SessionStart: inject UTC time + resumption protocol reminder ---
if [ "$hook_event" = "SessionStart" ]; then
    _binfo=$(python3 -c "
import json, sys
try:
    d = json.loads(sys.argv[1])
    cwd = (d.get('cwd') or '').replace('\\\\\\\\', '/').rstrip('/')
    workspace = cwd.split('/')[-1] if cwd else 'unknown'
    session_id = d.get('session_id', 'unknown') or 'unknown'
    print(workspace)
    print(session_id)
except Exception:
    print('unknown')
    print('unknown')
" "$raw" 2>/dev/null || printf 'unknown\nunknown\n')
    _workspace=$(printf '%s' "$_binfo" | sed -n '1p')
    _session_id=$(printf '%s' "$_binfo" | sed -n '2p')
    _border=$(printf '%54s' | tr ' ' '#')
    {
        printf '%s\n' "$_border"
        printf '#  %48s  #\n' ''
        printf '#  %-48s  #\n' 'SESSION START'
        printf '#  %-48s  #\n' "Workspace : $_workspace"
        printf '#  %-48s  #\n' "Session   : $_session_id"
        printf '#  %-48s  #\n' "Time      : $now_utc"
        printf '#  %48s  #\n' ''
        printf '%s\n' "$_border"
    } >&2
    system_message="[SessionStart] Current UTC time: $now_utc

Follow the Session Resumption Protocol (AGENTS.md): check /memories/session/ and /memories/repo/ before beginning work."
    python3 -c "import json, sys; print(json.dumps({'systemMessage': sys.argv[1]}))" "$system_message"
    exit 0
fi

# --- All other hooks: log-only, pass through ---
echo "{}"
