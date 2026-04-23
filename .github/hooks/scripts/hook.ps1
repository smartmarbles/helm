# Generic Copilot agent hook script
# Handles: SessionStart, UserPromptSubmit, PreToolUse, PostToolUse,
#          PreCompact, SubagentStart, SubagentStop, Stop
# Logs all events to .agent-memory/session/hook-log.jsonl
# Requires: Windows PowerShell 5.1+ or PowerShell 7+ (pwsh)

# --- Read stdin ---
$raw = [Console]::In.ReadToEnd()

$hook_event = "unknown"
$agent_name = "unknown"
$tool_name  = ""
$payload    = $null

if ($raw) {
    try {
        $payload    = $raw | ConvertFrom-Json -ErrorAction Stop
        $hook_event = if ($payload.PSObject.Properties['hook_event_name'] -and $payload.hook_event_name) { $payload.hook_event_name }
                      elseif ($payload.PSObject.Properties['hookEventName'] -and $payload.hookEventName) { $payload.hookEventName }
                      else { "unknown" }
        $agent_name = "unknown"
        foreach ($k in @('agent_type', 'agentName', 'agent_name', 'agent')) {
            if ($payload.PSObject.Properties[$k] -and $payload.$k) {
                $agent_name = [string]$payload.$k
                break
            }
        }
        $tool_name = if ($payload.PSObject.Properties['tool_name'] -and $payload.tool_name) { $payload.tool_name } else { "" }
        # For PreToolUse/runSubagent, agentName is nested inside tool_input
        if ($agent_name -eq "unknown" -and $payload.PSObject.Properties['tool_input'] -and $payload.tool_input) {
            foreach ($k in @('agentName', 'agent_name', 'agent_type', 'agent')) {
                if ($payload.tool_input.PSObject.Properties[$k] -and $payload.tool_input.$k) {
                    $agent_name = [string]$payload.tool_input.$k
                    break
                }
            }
        }
    } catch {
        # Non-blocking: proceed with defaults
    }
}

$now_utc = [System.DateTime]::UtcNow.ToString("yyyy-MM-dd HH:mm:ss UTC")
$now_iso  = [System.DateTime]::UtcNow.ToString("o")

# --- Write audit log ---
$log_dir = ".agent-memory/session"
if (-not (Test-Path $log_dir)) {
    New-Item -ItemType Directory -Path $log_dir -Force | Out-Null
}

# --- Agent state tracking ---
$state_file = "$log_dir/agent-state.json"
$tracked_state = $null
if (Test-Path $state_file) {
    try {
        $tracked_state = Get-Content $state_file -Raw -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
    } catch {}
}
if (-not $tracked_state) {
    $tracked_state = [PSCustomObject]@{ current = "ARTHUR"; stack = @() }
}
# If payload didn't identify an agent, fall back to tracked state
if ($agent_name -eq "unknown") {
    $agent_name = $tracked_state.current
}

$log_entry = [PSCustomObject]@{
    event     = $hook_event
    agent     = $agent_name
    tool      = $tool_name
    timestamp = $now_iso
    payload   = $payload
} | ConvertTo-Json -Compress -Depth 10

Add-Content -Path "$log_dir/hook-log.jsonl" -Value $log_entry -Encoding UTF8

# --- Update agent state ---
if ($hook_event -eq "SessionStart") {
    [PSCustomObject]@{ current = "ARTHUR"; stack = @() } | ConvertTo-Json -Compress |
        Set-Content $state_file -Encoding UTF8
} elseif ($hook_event -eq "SubagentStart") {
    $stack = @()
    if ($tracked_state.PSObject.Properties['stack'] -and $null -ne $tracked_state.stack) {
        $stack = @($tracked_state.stack)
    }
    $stack += @($tracked_state.current)
    [PSCustomObject]@{ current = $agent_name; stack = $stack } | ConvertTo-Json -Compress |
        Set-Content $state_file -Encoding UTF8
} elseif ($hook_event -eq "SubagentStop") {
    $stack = @()
    if ($tracked_state.PSObject.Properties['stack'] -and $null -ne $tracked_state.stack) {
        $stack = @($tracked_state.stack)
    }
    if ($stack.Count -gt 0) {
        $parent = $stack[-1]
        $new_stack = if ($stack.Count -gt 1) { $stack[0..($stack.Count - 2)] } else { @() }
    } else {
        $parent = "ARTHUR"
        $new_stack = @()
    }
    [PSCustomObject]@{ current = $parent; stack = $new_stack } | ConvertTo-Json -Compress |
        Set-Content $state_file -Encoding UTF8
}

# --- SubagentStart: look up and inject session checkpoint ---
if ($hook_event -eq "SubagentStart") {
    if ($agent_name -ne "unknown" -and $agent_name) {
        $slug = $agent_name.ToLower()
        $checkpoint_files = Get-ChildItem -Path $log_dir -Filter "$slug-*.md" -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending
        if ($checkpoint_files) {
            $checkpoint_content = Get-Content -Path $checkpoint_files[0].FullName -Raw -ErrorAction SilentlyContinue
            $system_message = "[SubagentStart] Current UTC time: $now_utc`n`nA prior session checkpoint was found for agent '$agent_name'. Resume from it:`n`n$($checkpoint_content.Trim())"
        } else {
            $system_message = "[SubagentStart] Current UTC time: $now_utc`n`nNo prior session checkpoint found. Follow the Session Resumption Protocol (AGENTS.md): check /memories/session/ and /memories/repo/ before beginning work."
        }
    } else {
        $system_message = "[SubagentStart] Current UTC time: $now_utc"
    }
    [PSCustomObject]@{ systemMessage = $system_message } | ConvertTo-Json -Compress
    exit 0
}

# --- SessionStart: inject UTC time + resumption protocol reminder ---
if ($hook_event -eq "SessionStart") {
    $workspace   = if ($payload -and $payload.PSObject.Properties['cwd'] -and $payload.cwd) { Split-Path -Leaf ([string]$payload.cwd) } else { "unknown" }
    $session_val = if ($payload -and $payload.PSObject.Properties['session_id'] -and $payload.session_id) { [string]$payload.session_id } else { "unknown" }
    $border = "#" * 54
    $blank  = "#  " + (" " * 48) + "  #"
    $banner = @(
        $border, $blank,
        ("#  {0,-48}  #" -f "SESSION START"),
        ("#  {0,-48}  #" -f "Workspace : $workspace"),
        ("#  {0,-48}  #" -f "Session   : $session_val"),
        ("#  {0,-48}  #" -f "Time      : $now_utc"),
        $blank, $border
    ) -join "`n"
    Write-Host $banner
    $system_message = "[SessionStart] Current UTC time: $now_utc`n`nFollow the Session Resumption Protocol (AGENTS.md): check /memories/session/ and /memories/repo/ before beginning work."
    [PSCustomObject]@{ systemMessage = $system_message } | ConvertTo-Json -Compress
    exit 0
}

# --- All other hooks: log-only, pass through ---
Write-Output "{}"
