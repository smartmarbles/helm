# AI Team — Workspace Context

This workspace uses an AI team orchestration system. All agents will be aware of the team structure and operating protocols described here.

## Team Structure

- **Roster**: `.github/team-roster.md` — all active and archived members
- **Agents**: `.github/agents/*.agent.md` — permanent team members
- **Temps**: `.github/agents/temps/` — completed temporary agents

## When Operating as a Specific Agent

When a user selects a specific agent (SCOOP, SAGE, QUILL, MERLIN, etc.), follow that agent's own instructions. The team structure above is context — not a directive to override the selected agent's behavior.

## Artifacts

Project artifacts (specs, plans, research, tasks) live in `artifacts/spec###-short-name/` folders, numbered sequentially with a descriptive kebab-case suffix (e.g., `artifacts/spec004-user-auth/`). Check `artifacts/` for existing `spec###-*` folders before creating new ones.

Standalone documentation (not tied to a spec workflow) lives in `artifacts/docs/`.

**Ownership**: ARTHUR assigns spec folder names and numbers. SAGE creates the folders. All other agents write to the folder specified in their task brief — never create spec folders themselves.

## Memory Scope Convention

Copilot's memory tool exposes three scopes, distinguished by path prefix. Agents choose the correct scope based on **content portability** — who should see this, and for how long. The extension routes by prefix automatically; no config file or namespace subfolder is involved.

| Scope | Path prefix | Write here when… |
|-------|-------------|------------------|
| **Session** | `/memories/session/` | Working state for the current task — checkpoints, handoff notes, in-progress outlines. Cleared or superseded when the task ends. |
| **Repo** | `/memories/repo/` | Durable project knowledge — conventions, architectural decisions, verified facts about this codebase. Survives across sessions within this workspace. |
| **User** | `/memories/` | Content that genuinely crosses projects — personal preferences, language-agnostic lessons, cross-workspace tooling notes. Rare. |

### Default: write durable project knowledge to `/memories/repo/`

When in doubt between user and repo scope, choose **repo**. Project-specific insights belong with the project.

### Warning: user scope leaks across workspaces

> **Warning:** The first 200 lines of every file under `/memories/` are loaded into **every Copilot session in every workspace** on this machine. A note written here during one project will appear in the context of every unrelated project thereafter.

Do not write to `/memories/` unless the content is explicitly cross-project. Project-specific names, paths, decisions, and conventions must go to `/memories/repo/` instead. A misfiled user-scope note is effectively a context leak into every future session.

### Non-decisions (stated so they are not re-litigated)

- **No dedicated config file** — scope selection is a writing discipline, not a configured namespace.
- **No project subfolders under `/memories/`** (e.g., no `/memories/my-project/`) — the three built-in scopes are sufficient. The path prefix *is* the namespace.
- **No tooling enforcement** — agents choose the scope correctly by convention. Misfiled notes are corrected by moving the file, not by validation machinery.

### Fallback Memory Structure

When the Copilot memory tool is unavailable at session startup, agents degrade to a local on-disk fallback rooted at `.agent-memory/` in the workspace. The fallback mirrors the repo and session scopes only:

```
.agent-memory/
├── session/   # session-scoped notes (equivalent to /memories/session/)
└── repo/      # repo-scoped notes (equivalent to /memories/repo/)
```

**No user scope.** User memory lives in VS Code's `globalStorage`, which is not reachable from the workspace. There is no safe way to fake it locally, so degraded agents operate without user-scope memory. (FR-021)

**Why only session + repo.** Both map cleanly to workspace-relative directories, are safe to write from any agent, and are already scoped to the current project. User memory's cross-workspace persistence cannot be replicated without access to the Copilot memory tool.

**Gitignored.** `.agent-memory/` is listed in `.gitignore` so fallback notes never leak into commits.

#### `[no-memory]` Notification Rule

When an agent detects memory unavailability at startup and falls back to `.agent-memory/`, it must inform the user that it is operating in degraded mode:

- **Prepend `[no-memory]` to the agent's final reply exactly once per session.**
- After the first prepend, a sentinel file is written to suppress further prepends for the remainder of the session.

**Sentinel file:** `.agent-memory/.notified-this-session`

- Created on the first degraded reply, immediately before returning.
- Its presence signals "user has already been notified this session" — subsequent replies in the same session MUST NOT prepend `[no-memory]` again.
- The sentinel is session-scoped by convention. A fresh session (new conversation) starts by re-evaluating memory availability and, if still degraded, will re-create the sentinel and re-notify on its first reply.

#### Mid-Session Memory Flicker

Memory tool availability is evaluated **once at session startup** and the result is sticky for the life of the session.

- If memory was available at startup and becomes unavailable later in the session, agents continue operating as if memory is available. They do not switch to fallback mid-session and do not prepend `[no-memory]`.
- If memory was unavailable at startup and becomes available later, agents continue operating in fallback mode against `.agent-memory/`. They do not migrate or re-probe.
- **Agents do not re-probe memory availability mid-session.** Mode is detected at startup and remains fixed until the session ends.

This prevents inconsistent behaviour, partial writes split across both backends, and repeated user-facing notifications within a single conversation.

---

# Session Resumption Protocol

This protocol applies to **every agent, regardless of memory-tool availability**. Follow it on every task. An agent that does not have the memory tool granted still persists checkpoints — it just writes them to a workspace-local fallback location instead of the memory store. Agents never rely on in-conversation state alone for anything they need to resume or hand off.

## Checkpoint Locations

Each agent's profile determines where checkpoints are written. The path layout is identical; only the root differs.

| Profile | Session checkpoints | Durable knowledge |
|---|---|---|
| Memory-enabled (memory tool granted) | `/memories/session/<agent>-<slug>.md` | `/memories/repo/` |
| Memory-less (memory tool not granted, or probe fails) | `.agent-memory/session/<agent>-<slug>.md` | `.agent-memory/repo/` |

- `<agent>` is the agent's lowercase slug (e.g., `sage`, `quill`, `scoop`, `arthur`).
- `<slug>` is a short kebab-case identifier for the task or spec (e.g., `spec002-agent-system-hardening`, `readme-refresh`).
- Per-agent filenames prevent collisions when multiple agents checkpoint against the same workspace.
- `.agent-memory/` is gitignored; it is the degraded-mode fallback, not shared persistence.

Memory-less agents detect their profile at startup by probing `view /memories/session/`. If the probe fails, they switch to the `.agent-memory/` root and prepend `[no-memory]` to their final reply once per session (see FR-018).

## Before Starting Any Task

1. Check the session checkpoint location for your profile (`/memories/session/` or `.agent-memory/session/`) for in-progress work from a prior session. If a checkpoint for this task exists, resume from the recorded position rather than starting over.
2. Check the durable-knowledge location for your profile (`/memories/repo/` or `.agent-memory/repo/`) for persistent project conventions, patterns, and key decisions that inform your work.
3. **ARTHUR only:** Also check `artifacts/` for spec folders with unchecked tasks in `plan.md` or `tasks.md`. If active work exists, summarize state and ask the user whether to continue or start fresh. Other agents skip this step.

## While Working

Checkpoint proactively **after each major unit of completed work, not only at phase boundaries**. A checkpoint is a write to your profile's session location that records enough state to resume cleanly if the session ends unexpectedly. Treat checkpointing as part of finishing a unit of work, not a cleanup step at the end.

At minimum, every checkpoint includes:

- What you're working on (task description, target files or spec folder)
- What is complete (section names, phase IDs, file paths written so far)
- What remains (the outline or task list of incomplete work)
- Key decisions made so far that affect the remaining work

Each agent's definition file specifies the additional checkpoint detail relevant to that agent's work.

## After Completing a Task

- **Delete your own session checkpoint file** (e.g., `.agent-memory/session/<agent>-<slug>.md` or `/memories/session/<agent>-<slug>.md`). A completed task's checkpoint is stale — leaving it behind risks a future session resuming finished work. If the checkpoint contains notes worth preserving long-term, move the relevant content to your durable-knowledge location (`/memories/repo/` or `.agent-memory/repo/`) before deleting the session file.
- For ARTHUR: after completing a Standard or Full Path effort, save reusable discoveries (conventions, patterns, key file locations) to your profile's durable-knowledge location (`/memories/repo/` or `.agent-memory/repo/`).

**Note on `.agent-memory/session/` lifecycle:** Unlike `/memories/session/` where VS Code manages cleanup automatically, the on-disk fallback has no automatic purge. Agents are responsible for deleting their own checkpoint files after task completion. Stale files from crashed or interrupted sessions may accumulate; they are harmless (gitignored) and agents should check file relevance before resuming from any checkpoint they find.

## Orchestrator-mediated checkpointing (memory-less subagents)

> **ARTHUR-specific relay rule.** Applies only when ARTHUR is re-dispatching a subagent that lacks the memory tool.

Subagents that do not have the `vscode/memory` tool granted in their frontmatter (all temp agents by default, plus any permanent agent running in a memory-less profile) cannot read or write `/memories/` directly. Instead, they write checkpoints to the workspace-local fallback path `.agent-memory/session/<agent>-<slug>.md` (gitignored). Because a memory-less subagent cannot read that file back on its next dispatch — each invocation starts with a clean conversation and no memory tool — ARTHUR performs the relay. Before re-dispatching any memory-less subagent, ARTHUR reads the agent's most recent `.agent-memory/session/<agent>-*.md` file and re-injects the relevant prior-dispatch context (completed work, outstanding items, key decisions) into the new dispatch brief. This makes ARTHUR the resumption channel for memory-less agents: the agent persists state to disk, ARTHUR carries it forward, and the agent resumes cleanly without ever needing the memory tool itself.
