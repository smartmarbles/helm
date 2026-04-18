# P2-T5 — Orchestrator-Mediated Checkpointing (Staged Copy)

> **Status:** Staged for Phase 4 application. Do not paste these blocks until the ARTHUR trim and AGENTS.md updates are scheduled. Both blocks below are ready to insert verbatim.

---

## Block A — For `AGENTS.md`

> Insert under the **Memory** section (or a new "Orchestrator-Mediated Checkpointing" subsection alongside it), after the existing description of `/memories/repo/` and `/memories/session/`.

### Orchestrator-mediated checkpointing (memory-less subagents)

Subagents that do not have the `vscode/memory` tool granted in their frontmatter (all temp agents by default, plus any permanent agent running in a memory-less profile) cannot read or write `/memories/` directly. Instead, they write checkpoints to the workspace-local fallback path `.agent-memory/session/<agent>-<slug>.md` (gitignored). Because a memory-less subagent cannot read that file back on its next dispatch — each invocation starts with a clean conversation and no memory tool — ARTHUR performs the relay. Before re-dispatching any memory-less subagent, ARTHUR reads the agent's most recent `.agent-memory/session/<agent>-*.md` file and re-injects the relevant prior-dispatch context (completed work, outstanding items, key decisions) into the new dispatch brief. This makes ARTHUR the resumption channel for memory-less agents: the agent persists state to disk, ARTHUR carries it forward, and the agent resumes cleanly without ever needing the memory tool itself.

---

## Block B — For `.github/agents/arthur.agent.md`

> Insert into ARTHUR's Delegation Protocol or Session Resumption section. Phrased to be ready-to-paste during the Phase 4 ARTHUR trim.

### Relaying checkpoints for memory-less subagents

Before re-dispatching any subagent that lacks `vscode/memory` (all temp agents, plus permanent agents configured without memory access), check `.agent-memory/session/<agent>-*.md` for a checkpoint left by that agent's prior dispatch. If one exists, read it and include the relevant prior-dispatch context — completed work, outstanding items, and key decisions — directly in the new dispatch brief. Memory-less subagents cannot read their own checkpoints back across dispatches; you are their resumption channel. Skip this step only when dispatching a subagent that has `vscode/memory` in its frontmatter (it will read `/memories/session/` itself) or when the subagent has no prior checkpoint on disk.

---

## Acceptance check

- [x] Block A present (AGENTS.md paragraph)
- [x] Block B present (ARTHUR agent-file paragraph)
- [x] Explicit rule encoded in both blocks: ARTHUR reads `.agent-memory/session/` for memory-less subagent output and relays context on re-dispatch
- [x] Staged file only — no edits to `AGENTS.md` or `arthur.agent.md` (deferred to Phase 4)
