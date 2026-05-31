# AI Team — Workspace Context

This workspace uses an AI team orchestration system. All agents follow the team structure and operating protocols described here.

## Team Structure

- **Roster**: `.github/team-roster.md` — all active and archived members
- **Agents**: `.github/agents/*.agent.md` — permanent team members
- **Temps**: `.github/agents/temps/` — completed temporary agents

> **Discovery constraint:** VS Code Copilot only discovers `.agent.md` files directly in `.github/agents/` — it does not recurse into subdirectories. Active temps must live in `.github/agents/` to remain invocable via `runSubagent`; archival to `temps/` makes them undiscoverable by design.

> **File Ordering Convention:** VS Code Copilot sorts agent instruction files (AGENTS.md, CLAUDE.md, copilot-instructions.md) by URI string (confirmed in source code). For other context types — `.instructions.md` files, skills, and custom agents — no ordering guarantee exists; observed alphabetical order on Windows is an NTFS filesystem artifact, not a platform contract. VS Code sorts skills by storage-priority tier (workspace before personal before plugin), not filename. Design all files to be self-contained — Do NOT rely on injection order for correctness.

## When Operating as a Specific Agent

When a user selects a specific agent (SCOOP, SAGE, QUILL, MERLIN, etc.), follow that agent's own instructions. The team structure above is context — not a directive to override the selected agent's behavior.

## Workflow Hygiene

Every agent follows these rules:

1. **Do NOT grep/list/existence-check docs mentioned in system prompts.** The system already injects them into context — re-reading wastes tokens. This applies to agent files, skill files, and workspace context files (e.g., AGENTS.md, copilot-instructions.md). It does NOT prohibit listing `artifacts/` to discover existing spec folder numbers — that directory listing is mandatory and separate from re-reading injected context.
2. **Read referenced docs only when directly relevant** — when you need the content for the task at hand, not preemptively.
3. **"Read X before doing anything" means once per session** — not before every sub-task.
4. **Every agent must follow the Session Resumption Protocol.** Every agent must check for prior checkpoints at task start.
5. **Concise output format:** Default to bullet summaries and one-line confirmations. No preamble. Errors shown in full; surrounding noise truncated with "full trace available on request". User overrides with "full summary" or "explain in detail."
6. **File-link-on-completion (MUST).** When any agent output is a file — whether returned to the user or as a subagent return message — the agent MUST return only the workspace-relative file path as a markdown link plus a one-line confirmation. The agent MUST NOT reprint, summarize, or excerpt file content unless explicitly asked. This rule takes precedence over the built-in `<communicationStyle>` defaults.
7. **Two files are already in your context — do not re-read them: `AGENTS.md` and `.github/copilot-instructions.md`.** Everything else (agent files, playbooks, skills, docs) — load when an explicit MANDATORY READ directive points to it, or when directly relevant to the task at hand.
8. **ADR Flagging (all agents)**: Any Helm agent that identifies an ADR candidate during its work must flag it in its return message to ARTHUR. An ADR candidate qualifies when all three conditions are true: (1) the decision is hard to reverse, (2) the decision would be surprising without context, (3) the decision came from a real trade-off. Upon receiving a flag, ARTHUR dispatches QUILL to write the polished ADR. This rule applies to every agent — it is not specific to QUIZ or SAGE.

## Dispatch Rules (agents that invoke subagents)

These rules apply to every agent that calls `runSubagent` — not only ARTHUR.

1. **ALWAYS use structured brief format.** Every `runSubagent` call MUST be structured as: **Objective / Constraints / Inputs / Expected Output**. Narrative prose dispatches are non-compliant.
2. **NEVER narrate a delegation without executing it.** Every delegation MUST include an actual `runSubagent` tool call in the same response. Writing "I'm dispatching X now" without a corresponding tool call is a protocol violation. If you catch yourself describing a delegation in text, STOP and emit the tool call immediately. A delegation that exists only in prose did not happen.
3. **NEVER fabricate or paraphrase error messages.** When a subagent dispatch or tool call fails, report the exact verbatim error text returned by the system. Do NOT infer, guess, paraphrase, or construct a plausible-sounding explanation. If the raw error is unavailable, say exactly that — "the system returned no error detail" — and stop. When reporting a blocker, include: what was attempted, the verbatim error (or "no error text available"), and what the user should do next.

## Output Strategies
An output strategy governs how an executing agent paces a deliverable within a single dispatch. By default, the agent produces the deliverable in one model response; ARTHUR may override this by adding an `Output Strategy` field to the brief.
- **`staged-writes`** - the agent divides the deliverable across multiple write/append operations against the same file within a single dispatch, confirming each section before proceeding. Triggered when ARTHUR includes `Output Strategy: staged-writes` in the brief. 

## Mandatory-Read Template

When an agent file references playbooks, use the pattern that matches the agent's playbook count:

**Single playbook** — use this block verbatim (substituting `<path>` only):

> **MANDATORY READ — `<path>`**
>
> Before performing this task, you MUST read `<path>` in full. This is not optional. Do not improvise from memory. If the file cannot be loaded, STOP and report the failure — do not proceed without it. Failure to load is a protocol violation.

**Multiple playbooks** — list each with a one-line purpose description, then add a single conditional instruction:

> ## Playbooks
>
> **MANDATORY READ — select the playbook that matches your task:**
>
> - **\<name\>** — `<path>` — \<one-line description of when to use it\>
>
> The playbook corresponding to your task MUST be read in full before proceeding. This is not optional. Do not improvise from memory. Do not read playbooks that do not apply to the current task. If it cannot be loaded, STOP and report the failure — do not proceed without it. Failure to load is a protocol violation.

## Artifacts

Project artifacts (specs, plans, research, tasks) live in `artifacts/spec###-short-name/` folders. Always assign the next unused sequential number (e.g., if spec006 exists, use spec007). Check `artifacts/` for all existing `spec###-*` folders before creating a new one.

Standalone documentation lives in `artifacts/docs/`.

**Ownership**: ARTHUR assigns spec folder names and numbers. SAGE creates the folders. All other agents write to the folder in their task brief — they must not create spec folders themselves.

## Memory Scope

Memory scopes follow built-in `<memoryInstructions>`. **DEFAULT to `/memories/repo/`** for project knowledge; `/memories/` only for genuinely cross-project content.

## Session Resumption Protocol

BEFORE STARTING ANY TASK — complete all steps that apply to your role:

1. Check `/memories/session/<your-agent>-*.md` for a prior checkpoint. If found, resume from it.
2. Check `/memories/repo/` for project conventions relevant to your task.
3. ARTHUR only: Check `artifacts/` for active spec work. Ask user: continue or start fresh.
4. ARTHUR only: Check the team roster for completed temps. Engage MERLIN to archive.

WHILE WORKING: After each major unit of completed work, write a checkpoint to `/memories/session/<agent>-<slug>.md`. Record: what is complete, what remains, key decisions made.

AFTER COMPLETING: Delete your session checkpoint file. Move any worth-keeping notes to `/memories/repo/` first.

Read `.github/docs/session-protocol.md` for full checkpoint detail, per-agent requirements, and orchestrator relay.

## Memory-less Operation

If the memory tool probe fails at startup (`view /memories/session/`), switch to `.agent-memory/` as the root for all reads and writes, and prepend `[no-memory]` to your first reply this session.

Read `.github/docs/memory-fallback.md` for full detail.
