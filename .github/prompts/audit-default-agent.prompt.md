---
description: "Periodic audit of the VS Code default-agent system prompt against Helm's saved snapshot. Run every 2–3 months or when default-agent behavior changes are observed."
---

## Default-Agent Prompt Audit

The VS Code default-agent system prompt changes periodically. The safety floor in `copilot-instructions.md` is designed against a specific version of that prompt — new content may warrant additions or adjustments. A saved snapshot lives at `artifacts/docs/copilot_agent.md`.

**Procedure:**
1. Open VS Code's Chat Debug View (`Chat: Open Chat Debug View` from the command palette).
2. Start a new conversation with the default agent (no agent selected).
3. Send a minimal prompt (e.g., "Hello"). The debug view will show the full system prompt injected by VS Code.
4. Copy the system prompt content from the debug view.
5. Diff it against `artifacts/docs/copilot_agent.md` (the saved snapshot).
6. If the diff is non-empty, review each change:
   - **New rules or constraints** added by VS Code → consider whether they conflict with or complement Helm's orchestration rules. Port relevant ones to `copilot-instructions.md` or `AGENTS.md`.
   - **Removed content** → check whether Helm's rules depended on VS Code providing that context. Add it explicitly if needed.
   - **Formatting changes only** → no action required.
7. Update `artifacts/docs/copilot_agent.md` with the latest snapshot after completing the review.

**No fixed agent owner.** Any maintainer runs this audit when due. No spec folder or formal plan is needed for routine audit runs.
