# P2-T2 — Universal Persistence Rule (staged prose)

Staged content for Phase 4 merge. Two drop-in blocks follow. Do not edit `AGENTS.md` or agent files from this file — ARTHUR owns the merge.

**Scope**: Implements FR-022 (universal persistence rule), FR-018 (memory-less fallback paths), FR-019 (per-agent checkpoint filenames).

---

## Block A — Replacement for `AGENTS.md` Session Resumption Protocol

> Intended to replace the existing `# Session Resumption Protocol` section (and everything under it) in [AGENTS.md](../../AGENTS.md). Keep the preceding `## Memory` section and the `---` separator above.

```markdown
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

- Clear or update your session checkpoint file so stale state doesn't mislead a future session.
- For ARTHUR: after completing a Standard or Full Path effort, save reusable discoveries (conventions, patterns, key file locations) to your profile's durable-knowledge location (`/memories/repo/` or `.agent-memory/repo/`).
```

---

## Block B — Per-agent Session Resumption paragraph (reusable)

> Phase 4 pastes this into each permanent agent file's `## Session Resumption` section, replacing the existing short reference. Substitute `<agent>` with the agent's lowercase slug (e.g., `sage`, `quill`). Pick **one** of the two path lines based on the agent's memory profile and delete the other; leave the rest of the paragraph unchanged.

```markdown
## Session Resumption

Follow the universal Session Resumption Protocol in [AGENTS.md](../../AGENTS.md). This applies to every agent, regardless of memory-tool availability — never rely on in-conversation state alone for anything you need to resume or hand off.

- **Checkpoint target (memory-enabled profile):** `/memories/session/<agent>-<slug>.md`; durable knowledge to `/memories/repo/`.
- **Checkpoint target (memory-less profile):** `.agent-memory/session/<agent>-<slug>.md`; durable knowledge to `.agent-memory/repo/`.

**Before starting:** Read your profile's session file for this task (`<agent>-<slug>.md`). If it exists, resume from the next incomplete unit rather than redoing completed work.

**While working:** Update the checkpoint after each major unit of completed work, not only at phase boundaries. Record task description, what is complete, what remains, and any key decisions that affect remaining work.

**After completing:** Clear or update the checkpoint so stale state doesn't mislead a future session.
```

---

## Notes for Phase 4 merge

- Block A fully replaces the current Session Resumption Protocol in `AGENTS.md` (lines under `# Session Resumption Protocol`). The `## Memory` section and `---` separator above it stay as-is.
- Block B is drop-in per agent. For agents whose profile is unambiguous, keep only the applicable checkpoint-target bullet. For agents whose profile may vary (e.g., dispatched with or without memory frontmatter), keep both bullets.
- Verbatim phrasings required by the spec are preserved:
  - "every agent, regardless of memory-tool availability" (Block A opening; Block B opening)
  - "after each major unit of completed work, not only at phase boundaries" (Block A While Working; Block B While working)
- Path encodings required by the spec:
  - Memory-enabled: `/memories/session/<agent>-<slug>.md`, durable to `/memories/repo/`
  - Memory-less: `.agent-memory/session/<agent>-<slug>.md`, durable to `.agent-memory/repo/`
