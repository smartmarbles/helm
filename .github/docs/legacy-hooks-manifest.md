# Legacy hooks manifest — `.github/docs/hooks.json`

`.github/docs/hooks.json` is the **superseded host hook-registration manifest**. It is kept here for historical reference only. Nothing loads it.

## What it was

It registered all eight hook events (`SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `SubagentStart`, `SubagentStop`, `Stop`) to a **single shared shell/PowerShell script** — `.github/hooks/scripts/hook.sh` / `hook.ps1` — using per-OS keys (`command` / `windows` / `osx`).

## What replaced it

`.github/hooks/helm.json` is the active manifest. It registers **each event to its own dedicated per-event Python wrapper** (`pre-tool-use.py`, `post-tool-use.py`, `session-start.py`, `stop.py`, `subagent-start.py`, `subagent-stop.py`, `user-prompt-submit.py`, `pre-compact.py`) via `python3` / `py -3`.

## Why it was moved (not deleted)

- It was moved out of `.github/hooks/` **specifically so it is not picked up alongside — or does not interfere with — the new `helm.json` manifest**.
- It was **relocated rather than deleted to preserve it for historical reference**.
- It is **no longer on any runtime load path**: no Python code reads it. The runtime engine `.github/hooks/_helm_hook.py` reads only `helm-controller.toml` plus runtime marker files (`.helm-controller.port`, `.helm-suspend`, `.helm-controller.lock`). `docs/hooks.json` is inert reference material.

> **Note:** This move had no prior recorded rationale in git commit messages or in `artifacts/spec015-orchestration-runtime-control/`. This file is that missing record.
