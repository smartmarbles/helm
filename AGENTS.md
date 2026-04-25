# AI Team — Workspace Context

This workspace uses an AI team orchestration system. All agents will be aware of the team structure and operating protocols described here.

## Team Structure

- **Roster**: `.github/team-roster.md` — all active and archived members
- **Agents**: `.github/agents/*.agent.md` — permanent team members
- **Temps**: `.github/agents/temps/` — completed temporary agents

> **Discovery constraint:** VS Code Copilot only discovers `.agent.md` files directly in `.github/agents/` — it does not recurse into subdirectories. Active temps must be moved to `.github/agents/` to be invocable via `runSubagent`; archival to `temps/` makes them undiscoverable by design.

> **File Ordering Convention:** VS Code Copilot sorts agent instruction files (AGENTS.md, CLAUDE.md, copilot-instructions.md) by URI string (confirmed in source code). For other context types — `.instructions.md` files, skills, and custom agents — no ordering guarantee exists; observed alphabetical order on Windows is an NTFS filesystem artifact, not a platform contract. Skills are sorted by storage-priority tier (workspace before personal before plugin), not filename. Design all files to be self-contained — never rely on injection order for correctness.

## When Operating as a Specific Agent

When a user selects a specific agent (SCOOP, SAGE, QUILL, MERLIN, etc.), follow that agent's own instructions. The team structure above is context — not a directive to override the selected agent's behavior.

## Workflow Hygiene

Every agent follows these rules:

1. **Do not grep/list/existence-check docs mentioned in system prompts.** They are already injected into context — re-reading wastes tokens.
2. **Read referenced docs only when directly relevant** — when you need the content for the task at hand, not preemptively.
3. **"Read X before doing anything" means once per session** — not before every sub-task.
4. **The Session Resumption Protocol is always required.** Checking for prior checkpoints at task start is mandatory.
5. **Fresh-conversation hygiene:** When switching tasks, open a new conversation. Chat history is injected with every message — long sessions carry full overhead into unrelated tasks and weaker models lose track of original constraints.
6. **Concise output format:** Default to bullet summaries and one-line confirmations. No preamble. Errors shown in full; surrounding noise truncated with "full trace available on request". User overrides with "full summary" or "explain in detail."
7. **File-link-on-completion:** When output is a file, return the file path link and a one-line confirmation only. Do not reprint or summarize file content unless asked.

## Artifacts

Project artifacts (specs, plans, research, tasks) live in `artifacts/spec###-short-name/` folders, numbered sequentially (e.g., `artifacts/spec004-user-auth/`). Check `artifacts/` for existing `spec###-*` folders before creating new ones.

Standalone documentation lives in `artifacts/docs/`.

**Ownership**: ARTHUR assigns spec folder names and numbers. SAGE creates the folders. All other agents write to the folder in their task brief — never create spec folders themselves.

## Memory Scope

| Scope | Path prefix | Write here when… |
|-------|-------------|------------------|
| **Session** | `/memories/session/` | Working state — checkpoints, handoff notes, in-progress outlines. |
| **Repo** | `/memories/repo/` | Durable project knowledge — conventions, decisions, verified facts. |
| **User** | `/memories/` | Content that genuinely crosses projects. Rare. |

**DEFAULT: Write project knowledge to `/memories/repo/`.** Write to `/memories/` only for content that genuinely crosses projects.

> **WARNING:** Files under `/memories/` load into every Copilot session on this machine — do not write project-specific content there.

## Session Resumption Protocol

BEFORE STARTING ANY TASK — complete all steps that apply to your role:

1. Check `/memories/session/<your-agent>-*.md` for a prior checkpoint. If found, resume from it.
2. Check `/memories/repo/` for project conventions relevant to your task.
3. ARTHUR only: Check `artifacts/` for active spec work. Ask user: continue or start fresh.
4. ARTHUR only: Check the team roster for completed temps. Engage MERLIN to archive.

WHILE WORKING: After each major unit of completed work, write a checkpoint to `/memories/session/<agent>-<slug>.md`. Record: what is complete, what remains, key decisions made.

AFTER COMPLETING: Delete your session checkpoint file. Move any worth-keeping notes to `/memories/repo/` first.

Full detail on checkpoint content, per-agent requirements, and orchestrator relay: `.github/docs/session-protocol.md`

## Memory-less Operation

If the memory tool probe fails at startup (`view /memories/session/`), switch to `.agent-memory/` as the root for all reads and writes, and prepend `[no-memory]` to your first reply this session.

Full detail: `.github/docs/memory-fallback.md`
