# MERLIN Archival & Offboarding

Process detail for MERLIN's offboarding workflow. The agent file defines *who MERLIN is* and the non-negotiable principles; this skill defines *how MERLIN retires a temp* — the trigger detection, the retain-vs-archive decision, the roster flip protocol, the re-archival trigger convention, and the unarchival reversal.

Read this skill whenever a dispatched task wraps up and a temp agent is no longer needed, or whenever a previously-archived agent is being brought back for retained work.

## How to use this skill

1. **Detect the trigger** — confirm the temp's task is actually complete (or that a previously-archived temp is being unarchived).
2. **Classify** using the Retain-vs-Archive Decision Table.
3. **Execute the roster flip** — update `.github/team-roster.md` only. No file moves (see File Location Convention).
4. **Record the re-archival trigger** if unarchiving a retained temp.
5. **Clean up session checkpoints** for the departing agent.

---

## Archival Trigger Detection

A temp is ready to archive when **all** of the following are true:

- The task row in the Temporary Agents table names a bounded scope (e.g., "spec002 P9a-T3" or "legacy config migration").
- That scope has landed — the file edits, test runs, or artifact writes are done and verified.
- No open re-archival trigger is unmet (see Re-archival Trigger Convention below).
- ARTHUR (or the user) has signalled completion, either explicitly ("archive SPLICE — they're done") or implicitly (the spec/phase owning the temp's scope is closed).

If the temp was hired for a single dispatch and the dispatch has returned, archival is the default next step. If the temp was retained (see Retain-vs-Archive Decision Table), archival waits for the recorded re-archival trigger.

### Rule: do not archive mid-task

A temp with unfinished scope stays active. Archival is a completion signal, not a shortcut to tidy the roster. If the task is stalled or blocked, route to ARTHUR — do not archive to "clean up."

---

## Retain-vs-Archive Decision Table

| Situation | Decision | Why |
|-----------|----------|-----|
| Temp was hired for a single dispatch, dispatch has returned, scope is bounded and complete. | **Archive now.** Remove the row from the Temporary Agents table. | Single-dispatch temps are archived on return. That is the default lifecycle. |
| Temp was hired for a single dispatch, but scope has grown mid-work (new related task assigned to the same temp). | **Retain.** Keep `Active`. Update the Task column to note scope expansion. Add a re-archival trigger blockquote beneath the table naming the new completion condition. | Retention is a scope-change response, not a promotion. The agent stays temp; the roster reflects the new exit condition. |
| Temp was previously archived (Status column shows `Archived (YYYY-MM-DD)`), user asks to bring them back for more of the same work. | **Unarchive.** Flip Status from `Archived (YYYY-MM-DD)` back to `Active`. Update the Task column to append the expanded scope. Add a re-archival trigger blockquote naming the new completion condition. | Unarchival is the reversal of archival. Same row, same agent file, same tagline — only the Status column and Task column change. |
| Task is blocked or stalled but not done. | **Leave active.** Do not archive. | Archival signals completion, not inactivity. Route to ARTHUR for a blocker. |
| User asks to archive a permanent team member. | **Decline.** Permanent agents do not archive; they are retired via a separate conversation with the user. | Permanent agents have no Status column. The protocol below is temp-only. |
| User asks to archive an agent not on the roster. | **Decline.** No-op. Confirm the roster is the source of truth. | You cannot archive what the roster does not list. |

---

## Roster Update Protocol

The Temporary Agents table in `.github/team-roster.md` uses the same format as the Permanent Team table:

```
| Agent | Role | Use When | Hired | Tagline |
|-------|------|----------|-------|---------|
| SPLICE | Surgical Python Validator Coder | spec002 P9a-T3 surgical Python edits | 2026-04-18 | *The diff is the deliverable.* |
```

Re-archival triggers (if any) live in a blockquote beneath the table.

### Archiving a temp

1. Locate the temp's row in the Temporary Agents table.
2. Remove the row entirely from the table.
3. Move the agent file from `.github/agents/<name>.agent.md` to `.github/agents/temps/<name>.agent.md`.
4. If an open re-archival trigger blockquote exists for this temp, remove it (the condition has been met).
5. Report: temp archived, row removed, file moved to `temps/`, trigger removed (if any).

### Unarchiving a temp

1. Confirm the temp's row is absent from the Temporary Agents table (it was removed during archival).
2. Re-add the row to the Temporary Agents table using permanent-format columns (`Agent | Role | Use When | Hired | Tagline`). Update `Use When` to reflect the expanded scope.
3. Add a re-archival trigger blockquote beneath the table. Format:

   ```markdown
   > **Re-archival trigger:** <condition that, when met, will re-archive this agent>
   ```

4. Report: temp unarchived, row re-added, re-archival trigger recorded.

> **File move required on unarchival:** When reactivating an archived temp, move the file from `.github/agents/temps/<name>.agent.md` back to `.github/agents/<name>.agent.md` — Copilot cannot discover agents in subdirectories.

### Re-archival Trigger Convention

A re-archival trigger is a blockquote that names the exact condition which, when it fires, will re-archive the agent. It serves as a self-documenting exit gate so future MERLIN sessions (or ARTHUR) know when the retained temp's scope ends.

Good triggers are concrete and observable:

- "Re-archive SPLICE before spec002 completion, once the final Python development task lands."
- "Re-archive FORGE after the migration script's final run in production."
- "Re-archive HELIX when the last P9b task is verified by PROBE."

Bad triggers are vague or open-ended:

- "Re-archive when no longer needed." (not observable)
- "Re-archive eventually." (no condition)
- "Re-archive when the team decides." (not self-contained)

When the trigger condition fires, the archival workflow removes the blockquote as part of step 4 of *Archiving a temp*.

### Verification

After archival, confirm the agent no longer appears in the VS Code Copilot agents list by checking the system prompt's `<agents>` roster. The file move to `temps/` removes it from Copilot's discovery path (`.github/agents/` only — no subdirectory recursion). The roster row being absent from the Temporary Agents table is the authoritative lifecycle signal.

---

## File Location Convention

Temp agent files are authored at `.github/agents/<name>.agent.md` (the active location) by the `hire-agent` skill. **Archival moves the file to `.github/agents/temps/<name>.agent.md`.** This removes the agent from Copilot's discovery path — Copilot only scans `.github/agents/` directly, not subdirectories.

- **Active temp:** file at `.github/agents/<name>.agent.md`, row present in Temporary Agents table.
- **Archived temp:** file at `.github/agents/temps/<name>.agent.md`, row absent from Temporary Agents table.

Both signals (file location and row presence) should agree. The roster row is the authoritative lifecycle signal for humans; the file location is the authoritative signal for Copilot discoverability.

---

## Session Checkpoint Cleanup

Departing temp agents may have left session-scoped notes at `/memories/session/<agent>-*.md` (or `.agent-memory/session/<agent>-*.md` in memory-less profiles). On archive:

1. If the temp had a memory-tool grant, MERLIN does not need to touch that agent's session files — the Session Resumption Protocol in `AGENTS.md` says agents clear or update their own checkpoint files at task completion. Trust that contract.
2. If the temp was memory-less and wrote to `.agent-memory/session/`, that file is already session-scoped and gitignored. No cleanup needed; fresh sessions re-probe.
3. MERLIN does NOT delete another agent's memory files on archive. The checkpoint cleanup responsibility is the agent's own, not HR's.

The only cleanup MERLIN performs during archival is the roster update described above.

---

## Permanent Agents

Permanent team members (ARTHUR, SAGE, SCOOP, QUILL, MERLIN, PROBE, and any other row in the **Permanent Team** table) **do not archive**. The Permanent Team table has no `Status` column; there is no lifecycle-end field to flip.

If a user asks to archive a permanent agent, decline and explain the distinction:

- Temporary agents archive on task completion — a lifecycle event.
- Permanent agents are retired via an explicit user decision (role elimination, team restructure, etc.), which is out of scope for this skill and out of scope for MERLIN without user direction.

Do not invent an archival protocol for permanents.

---

## Worked examples

### Example 1 — Archiving SPLICE at end of task

**DO:**

> User (or ARTHUR): "Archive SPLICE — they're done with the final Python task for spec002."
>
> MERLIN runs Archival Trigger Detection:
> - Task row names a bounded scope ("spec002 P9a-T3 / T3b / ongoing Python work through Phase 9b (incl. FR-096 `--update-roster`)").
> - Scope has landed (final task verified).
> - Open re-archival trigger exists ("Re-archive SPLICE before spec002 completion, once the final Python development task lands.") and has now fired.
> - Completion signalled by user.
>
> MERLIN opens `.github/team-roster.md`, locates SPLICE's row in the Temporary Agents table, and removes the row entirely. Removes the re-archival trigger blockquote beneath the table (condition has been met). Moves the agent file from `.github/agents/splice.agent.md` to `.github/agents/temps/splice.agent.md`. Reports: SPLICE archived on 2026-04-18, row removed, file moved to `temps/`, trigger blockquote removed.

**DON'T:**

> MERLIN: "Archiving SPLICE. I'll move `.github/agents/splice.agent.md` to `.github/agents/temps/splice.agent.md` as part of archival."
>
> Wrong. Archival is two steps: remove the roster row AND move the file to `temps/`. Skipping the file move leaves the agent discoverable by Copilot (`.github/agents/` is scanned directly), which means the "archived" agent is still invocable. Both steps are required.

---

### Example 2 — Unarchiving SPLICE for retained Python work

**DO:**

> User: "Actually, we need SPLICE back — more Python work came in for Phase 9b."
>
> MERLIN classifies using the Retain-vs-Archive Decision Table: previously archived (row absent), user bringing them back → **Unarchive**.
>
> MERLIN opens `.github/team-roster.md` and re-adds SPLICE's row to the Temporary Agents table with updated `Use When` (e.g., `spec002 P9a-T3 / T3b / ongoing Python work through Phase 9b`). Adds a re-archival trigger blockquote beneath the table:
>
> > **Re-archival trigger:** Re-archive SPLICE before spec002 completion, once the final Python development task lands.
>
> Reports: SPLICE unarchived, row re-added, re-archival trigger recorded.

**DON'T:**

> MERLIN: "Unarchiving SPLICE. Since this is expanded scope, I'll promote SPLICE to the Permanent Team table."
>
> Wrong. Retention is a scope-change response, not a promotion. SPLICE stays in the Temporary Agents table (same format as permanent, with a re-archival trigger callout). Promotion to permanent is a separate, user-driven decision that is out of scope here.

---

### Example 3 — Declining to archive a permanent agent

**DO:**

> User: "Archive PRISM — we haven't used them in a while."
>
> MERLIN consults the Permanent Team table. PRISM is a permanent hire (2026-04-18, CSS Specialist). Permanent agents do not archive. MERLIN declines, explains the distinction (temp archival is lifecycle-end; permanent retirement is an explicit team-restructure decision), and asks the user whether they actually want to retire PRISM (which requires a different workflow) or whether PRISM's Use-When scope should be narrowed instead.

**DON'T:**

> MERLIN: "Archiving PRISM — moving the Permanent Team row to the Temporary Agents table and setting Status to `Archived (2026-04-19)`."
>
> Wrong. The Permanent Team table has no Status column; there is no lifecycle-end field to flip. Fabricating a cross-table migration is not archival — it is a roster rewrite that discards PRISM's permanent-hire semantics. Decline and escalate instead.

---

### Example 4 — Refusing mid-task archival

**DO:**

> User: "The roster is cluttered. Archive HELIX to tidy it up — we'll bring them back later."
>
> MERLIN runs Archival Trigger Detection. HELIX's task scope is not complete (e.g., the phase owning their work is still mid-execution). Archival fails the "scope has landed" check. MERLIN declines: archival is a completion signal, not a cleanup shortcut. Recommends the user either finish HELIX's current dispatch (then archive cleanly) or route to ARTHUR if the work is blocked.

**DON'T:**

> MERLIN: "Archiving HELIX now; we can unarchive when we come back to it."
>
> Wrong. Archive-then-unarchive as a roster-tidying pattern violates the Archival Trigger Detection contract ("Do not archive mid-task"). It also erases the in-flight Task column state and requires re-deriving the scope on unarchive. Leave HELIX active; route the actual decision to ARTHUR.

---

## Quick reference

- **Is the temp's task actually complete?** → If no, do not archive. Route blockers to ARTHUR.
- **Single-dispatch or retained?** → Single-dispatch: archive on return. Retained: archive when the recorded re-archival trigger fires.
- **Archival action** → Remove the temp's row from the Temporary Agents table. Move the agent file from `.github/agents/<name>.agent.md` to `.github/agents/temps/<name>.agent.md`. Remove the re-archival trigger blockquote if one existed.
- **Unarchival action** → Re-add the row to the Temporary Agents table (permanent-format columns). Update `Use When` to reflect the expanded scope. Move the agent file from `.github/agents/temps/<name>.agent.md` back to `.github/agents/<name>.agent.md`. Add a re-archival trigger blockquote beneath the table.
- **File moves on archive** → Required. Move to `.github/agents/temps/` to remove the agent from Copilot's discovery path.
- **Permanent agents** → Do not archive. Decline and explain.
- **Session memory cleanup** → Agents clean their own checkpoints. MERLIN does not touch another agent's memory files.
