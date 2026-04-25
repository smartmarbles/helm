# Session Resumption Protocol — Full Detail

> This file contains the full specification for agent session resumption, checkpointing, and orchestrator relay. The executable checklist every agent must follow is in `AGENTS.md`. Read this file when you need detail on checkpoint content, per-agent checkpoint requirements, checkpoint locations for memory-less agents, or orchestrator relay. For detection and `[no-memory]` notification rules, see `memory-fallback.md`.

---

## Checkpoint Locations

Each agent's profile determines where checkpoints are written. The path layout is identical; only the root differs.

| Profile | Session checkpoints | Durable knowledge |
|---|---|---|
| Memory-enabled (memory tool granted) | `/memories/session/<agent>-<slug>.md` | `/memories/repo/` |
| Memory-less (memory tool not granted, or probe fails) | `.agent-memory/session/<agent>-<slug>.md` | `.agent-memory/repo/` |

- `<agent>` — agent's lowercase slug (e.g., `sage`, `quill`, `scoop`, `arthur`)
- `<slug>` — short kebab-case task identifier (e.g., `spec002-agent-hardening`, `readme-refresh`)
- Per-agent filenames prevent collisions when multiple agents checkpoint in the same workspace.
- `.agent-memory/` is gitignored; it is the degraded-mode fallback, not shared persistence.

Memory-less agents detect their profile at startup by probing `view /memories/session/`. If the probe fails, switch to `.agent-memory/` root and prepend `[no-memory]` to the first reply (see `memory-fallback.md`).

---

## What to Include in Every Checkpoint

At minimum:

- Task description and target files or spec folder
- What is complete (section names, phase IDs, file paths written so far)
- What remains (outline or task list of incomplete work)
- Key decisions made that affect the remaining work

Agent-specific checkpoint requirements:

| Agent | Additional checkpoint content |
|---|---|
| ARTHUR | Active spec folder, current phase, completed phase IDs, remaining phases, blockers |
| QUILL | Target output folder, full section outline, filenames of completed sections, terminology and structural decisions |
| SAGE | Spec/plan file path, approved sections, open questions resolved, remaining sections |
| MERLIN | Candidate agent slug, hire vs. temp decision, SCOOP research status, `.agent.md` authoring progress |
| PROBE | Test plan path, completed TC-### IDs, scorecard state, outstanding failures |

---

## While Working

Checkpoint **after each major unit of completed work, not only at phase boundaries**. A checkpoint is a write to your profile's session location that records enough state to resume cleanly if the session ends unexpectedly.

Treat checkpointing as part of finishing a unit of work — not a cleanup step at the end.

---

## After Completing a Task

1. Delete your own session checkpoint file. A completed task's checkpoint is stale — leaving it causes a future session to resume finished work.
2. If the checkpoint contains notes worth preserving, move the relevant content to your durable-knowledge location (`/memories/repo/` or `.agent-memory/repo/`) before deleting.
3. ARTHUR: After completing a Standard or Full Path effort, save reusable discoveries (conventions, patterns, key file locations) to your durable-knowledge location.

**Note on `.agent-memory/session/` lifecycle:** Unlike `/memories/session/` where VS Code manages cleanup, the on-disk fallback has no automatic purge. Agents are responsible for deleting their own checkpoint files after task completion. Stale files from interrupted sessions are harmless (gitignored) — check file relevance before resuming from any checkpoint found.

---

## Orchestrator-Mediated Checkpointing (ARTHUR-specific)

> Applies only when ARTHUR is re-dispatching a subagent that lacks the memory tool.

Subagents without the `vscode/memory` tool granted in their frontmatter (all temp agents by default; any permanent agent in memory-less profile) cannot read or write `/memories/` directly. They write checkpoints to `.agent-memory/session/<agent>-<slug>.md`.

Because a memory-less subagent cannot read that file on its next dispatch (each invocation starts with a clean conversation), **ARTHUR performs the relay**:

1. Before re-dispatching any memory-less subagent, ARTHUR reads the agent's most recent `.agent-memory/session/<agent>-*.md` file.
2. ARTHUR re-injects the relevant prior-dispatch context (completed work, outstanding items, key decisions) into the new dispatch brief.
3. The agent resumes cleanly without ever needing the memory tool itself.

ARTHUR is the resumption channel for memory-less agents — the agent persists state to disk, ARTHUR carries it forward.
