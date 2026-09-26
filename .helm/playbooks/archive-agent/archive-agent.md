# MERLIN Archival & Offboarding

Process detail for MERLIN's offboarding workflow. The agent file defines *who MERLIN is* and the non-negotiable principles; this skill defines *how MERLIN retires a temp* — the trigger detection, the retain-vs-archive decision, the roster flip protocol, the re-archival trigger convention, and the unarchival reversal.

Read this skill whenever a dispatched task wraps up and a temp agent is no longer needed, or whenever a previously-archived agent is being brought back for retained work.

## How to use this skill

1. **Detect the trigger** — confirm the temp's task is actually complete (or that a previously-archived temp is being unarchived).
2. **Classify** using the Retain-vs-Archive Decision Table.
3. **Execute the roster flip and wrapper move** — update `.github/team-roster.md`, then move all four per-host wrapper files to/from their `temps/` paths (see File Location Convention). The authored source at `.helm/agents/<name>.md` never moves.
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
3. Move each of the temp's four host wrapper files from its active discovery path to that host's `temps/` path:
   - `.github/agents/<name>.agent.md` → `.github/agents/temps/<name>.agent.md`
   - `.claude/agents/<name>.md` → `.claude/agents/temps/<name>.md`
   - `.devin/agents/<name>.md` → `.devin/agents/temps/<name>.md`
   - `.cursor/agents/<name>.md` → `.cursor/agents/temps/<name>.md`

   Do **not** move or delete the authored source at `.helm/agents/<name>.md`. It is shared, host-agnostic content — retaining it costs nothing and lets the agent be un-archived and redeployed later without re-authoring.
4. If an open re-archival trigger blockquote exists for this temp, remove it (the condition has been met).
5. Report: temp archived, row removed, all four wrapper files moved to their `temps/` paths, authored source retained unchanged at `.helm/agents/<name>.md`, trigger removed (if any).

### Unarchiving a temp

1. Confirm the temp's row is absent from the Temporary Agents table (it was removed during archival).
2. Re-add the row to the Temporary Agents table using permanent-format columns (`Agent | Role | Use When | Hired | Tagline`). Update `Use When` to reflect the expanded scope.
3. Add a re-archival trigger blockquote beneath the table. Format:

   ```markdown
   > **Re-archival trigger:** <condition that, when met, will re-archive this agent>
   ```

4. Move each of the temp's four host wrapper files back from that host's `temps/` path to its active discovery path:
   - `.github/agents/temps/<name>.agent.md` → `.github/agents/<name>.agent.md`
   - `.claude/agents/temps/<name>.md` → `.claude/agents/<name>.md`
   - `.devin/agents/temps/<name>.md` → `.devin/agents/<name>.md`
   - `.cursor/agents/temps/<name>.md` → `.cursor/agents/<name>.md`

   The authored source at `.helm/agents/<name>.md` was never moved during archival, so there is nothing to restore for it.
5. Report: temp unarchived, row re-added, all four wrapper files restored to their active paths, re-archival trigger recorded.

> **Wrapper moves required on unarchival:** Every in-scope host discovers agents only at its own active path with no subdirectory recursion — restoring the roster row alone does not make the agent invocable again on any host. All four wrapper files must move back.

### Re-archival Trigger Convention

A re-archival trigger is a blockquote that names the exact condition which, when it fires, will re-archive the agent. It serves as a self-documenting exit gate so future MERLIN sessions (or ARTHUR) know when the retained temp's scope ends.

Good triggers are concrete and observable:

- "Re-archive SPLICE before spec002 completion, once the final Python development task lands."
- "Re-archive FORGE after the migration script's final run in production."
- "Re-archive HELIX when the last P9b task is verified by the test runner."

Bad triggers are vague or open-ended:

- "Re-archive when no longer needed." (not observable)
- "Re-archive eventually." (no condition)
- "Re-archive when the team decides." (not self-contained)

When the trigger condition fires, the archival workflow removes the blockquote as part of step 4 of *Archiving a temp*.

### Verification

After archival, confirm the agent no longer appears in the VS Code Copilot agents list by checking the system prompt's `<agents>` roster — this verifies the VS Code wrapper move only. Each other in-scope host (Claude Code, Devin Desktop, Cursor) has its own discovery mechanism and must be checked independently if that host is actively in use; the wrapper move to that host's `temps/` path removes it from that host's discovery path the same way (active directory only — no subdirectory recursion, on any host). The roster row being absent from the Temporary Agents table is the authoritative lifecycle signal across all hosts.

---

## File Location Convention

Every hired agent is represented by one host-agnostic authored source plus one thin wrapper per in-scope host (see `hire-agent`'s Agent File Schema). Archival and unarchival act **only on the wrapper files** — the authored source never moves.

### Authored source — never moves

`.helm/agents/<name>.md` stays at that same path for the agent's entire lifecycle, archived or not. It is shared, host-agnostic content that could be un-archived and reused later; deleting or moving it on archival would discard identity content that costs nothing to keep around.

### Per-host wrappers — active vs. archived path

| Host | Active path | Archived (`temps/`) path |
|---|---|---|
| VS Code Copilot | `.github/agents/<name>.agent.md` | `.github/agents/temps/<name>.agent.md` |
| Claude Code | `.claude/agents/<name>.md` | `.claude/agents/temps/<name>.md` |
| Devin Desktop | `.devin/agents/<name>.md` | `.devin/agents/temps/<name>.md` |
| Cursor | `.cursor/agents/<name>.md` | `.cursor/agents/temps/<name>.md` |

Archival moves **all four** wrapper files from their active path to their host's `temps/` path in the same operation. This removes the agent from every host's discovery path — each host scans only its own active directory, never a `temps/` subdirectory.

- **Active temp:** all four wrapper files at their active paths, authored source at `.helm/agents/<name>.md`, row present in Temporary Agents table.
- **Archived temp:** all four wrapper files at their `temps/` paths, authored source unchanged at `.helm/agents/<name>.md`, row absent from Temporary Agents table.

Both signals (wrapper file location and row presence) should agree. The roster row is the authoritative lifecycle signal for humans; wrapper file location is the authoritative signal for each host's discoverability.

---

## Session Checkpoint Cleanup

Departing temp agents may have left session-scoped notes in the host's own memory/scratch mechanism (`access-working-store`), or in a fallback session-scoped location when the host has none. On archive:

1. If the temp had access to the host's working-store mechanism, MERLIN does not need to touch that agent's session files — the Session Resumption Protocol in `AGENTS.md` says agents clear or update their own checkpoint files at task completion. Trust that contract.
2. If the temp was memory-less and used a fallback session-scoped location instead, that location is already session-scoped and excluded from version control. No cleanup needed; fresh sessions re-probe.
3. MERLIN does NOT delete another agent's memory files on archive. The checkpoint cleanup responsibility is the agent's own, not HR's.

The only cleanup MERLIN performs during archival is the roster update described above.

---

## Permanent Agents

Permanent team members (ARTHUR, SAGE, SCOOP, QUILL, MERLIN, and any other row in the **Permanent Team** table) **do not archive**. The Permanent Team table has no `Status` column; there is no lifecycle-end field to flip.

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
> - Task row names a bounded scope ("spec002 P9a-T3 / T3b / ongoing Python work through Phase 9b (incl. `--update-roster`)").
> - Scope has landed (final task verified).
> - Open re-archival trigger exists ("Re-archive SPLICE before spec002 completion, once the final Python development task lands.") and has now fired.
> - Completion signalled by user.
>
> MERLIN opens `.github/team-roster.md`, locates SPLICE's row in the Temporary Agents table, and removes the row entirely. Removes the re-archival trigger blockquote beneath the table (condition has been met). Moves all four host wrapper files — `.github/agents/splice.agent.md` → `.github/agents/temps/splice.agent.md`, `.claude/agents/splice.md` → `.claude/agents/temps/splice.md`, `.devin/agents/splice.md` → `.devin/agents/temps/splice.md`, `.cursor/agents/splice.md` → `.cursor/agents/temps/splice.md`. Leaves the authored source at `.helm/agents/splice.md` untouched. Reports: SPLICE archived on 2026-04-18, row removed, all four wrapper files moved to `temps/`, authored source retained, trigger blockquote removed.

**DON'T:**

> MERLIN: "Archiving SPLICE. I'll move `.github/agents/splice.agent.md` to `.github/agents/temps/splice.agent.md` as part of archival."
>
> Wrong. Archival requires moving **all four** host wrapper files, not just the VS Code one. Leaving `.claude/agents/splice.md`, `.devin/agents/splice.md`, or `.cursor/agents/splice.md` at their active paths means SPLICE is still discoverable and invocable on those hosts even after the roster row is removed. Every in-scope host's wrapper must move.

---

### Example 2 — Unarchiving SPLICE for retained Python work

**DO:**

> User: "Actually, we need SPLICE back — more Python work came in for Phase 9b."
>
> MERLIN classifies using the Retain-vs-Archive Decision Table: previously archived (row absent), user bringing them back → **Unarchive**.
>
> MERLIN opens `.github/team-roster.md` and re-adds SPLICE's row to the Temporary Agents table with updated `Use When` (e.g., `spec002 P9a-T3 / T3b / ongoing Python work through Phase 9b`). Moves all four host wrapper files back from `temps/` to their active paths — `.github/agents/temps/splice.agent.md` → `.github/agents/splice.agent.md`, `.claude/agents/temps/splice.md` → `.claude/agents/splice.md`, `.devin/agents/temps/splice.md` → `.devin/agents/splice.md`, `.cursor/agents/temps/splice.md` → `.cursor/agents/splice.md`. The authored source at `.helm/agents/splice.md` was never moved, so nothing changes there. Adds a re-archival trigger blockquote beneath the table:
>
> > **Re-archival trigger:** Re-archive SPLICE before spec002 completion, once the final Python development task lands.
>
> Reports: SPLICE unarchived, row re-added, all four wrapper files restored to their active paths, re-archival trigger recorded.

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
- **Archival action** → Remove the temp's row from the Temporary Agents table. Move all four host wrapper files (`.github/agents/`, `.claude/agents/`, `.devin/agents/`, `.cursor/agents/`) from their active path to that host's `temps/` path. Leave the authored source at `.helm/agents/<name>.md` untouched. Remove the re-archival trigger blockquote if one existed.
- **Unarchival action** → Re-add the row to the Temporary Agents table (permanent-format columns). Update `Use When` to reflect the expanded scope. Move all four host wrapper files back from their `temps/` path to their active path. The authored source never moved, so it needs no restoration. Add a re-archival trigger blockquote beneath the table.
- **File moves on archive** → Required for all four wrapper files, one per in-scope host. The authored source at `.helm/agents/<name>.md` NEVER moves or deletes — it is shared, reusable content.
- **Permanent agents** → Do not archive. Decline and explain.
- **Session memory cleanup** → Agents clean their own checkpoints. MERLIN does not touch another agent's memory files.
