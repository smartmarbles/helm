# P3-T5b Eval-Pass Walkthrough — `archive-agent` skill

Logical walkthrough verifying each eval prompt, when handled by MERLIN loading the `archive-agent` skill, produces behaviour that matches the skill's guidance and traces to `merlin.agent.md` — confined to archival/offboarding (hiring lives with the parallel `hire-agent` skill).

## Eval 1 — Archiving SPLICE at end of task

**Prompt:** "Archive SPLICE — they finished the final Python development task for spec002."

**Skill-directed behaviour:**
1. **Archival Trigger Detection** → task row names bounded scope ("spec002 P9a-T3 / T3b / ongoing Python work through Phase 9b"); scope has landed (user signals "they finished"); open re-archival trigger ("Re-archive SPLICE before spec002 completion, once the final Python development task lands") has now fired; completion signal explicit. All four conditions met → proceed.
2. **Retain-vs-Archive Decision Table** row 1 (single-dispatch-style completion / retained-temp trigger fired) → **Archive now.**
3. **Roster Update Protocol → Archiving a temp:**
   - Locate SPLICE's row in the Temporary Agents table.
   - Flip Archived from `*(active)*` to today's `YYYY-MM-DD` date.
   - `File` column untouched (File Location Convention: archival is a roster-state change, not a filesystem move).
   - Re-archival trigger blockquote removed (condition met).
   - Tagline callout left intact.
4. **Session Checkpoint Cleanup rule** → agents clean their own checkpoints; MERLIN does not touch SPLICE's memory files.
5. Reports the archival and trigger removal.

**Cross-check against `merlin.agent.md`:**
- Responsibility 6 ("Offboarding — Move temporary agents to `.github/agents/temps/` and update the roster") is reproduced in the skill but **reinterpreted** via the File Location Convention (no physical move; roster flag is the single source of truth). This matches the current repo state (SPLICE's `File` column already points under `temps/` from legacy authoring; new temps authored at active location stay there).
- "Do NOT create agents without updating the roster" constraint generalizes to "roster is the source of truth for lifecycle state" — reproduced in the archival protocol.

**Expectations satisfied:** all six (trigger detection; date flip; trigger blockquote removed; no file move; tagline intact; session-memory untouched).

## Eval 2 — Unarchiving SPLICE for retained Python work

**Prompt:** "Unarchive SPLICE — we need them again for more Python work in Phase 9b."

**Skill-directed behaviour:**
1. **Retain-vs-Archive Decision Table** row 3 (previously archived, user bringing them back) → **Unarchive.**
2. **Roster Update Protocol → Unarchiving a temp:**
   - Flip Archived from `YYYY-MM-DD` back to `*(active)*`.
   - Append new scope to Task column.
   - Add a re-archival trigger blockquote beneath the table with a concrete, observable condition (e.g., "Re-archive SPLICE before spec002 completion, once the final Python development task lands").
   - Tagline and `File` columns left untouched.
3. **Retention ≠ promotion rule** (Decision Table row 2 commentary + worked example 2 DON'T) → SPLICE stays in the Temporary Agents table; no migration to Permanent Team.
4. **Re-archival Trigger Convention** → trigger must be concrete and observable. Vague triggers ("when no longer needed") are rejected.

**Cross-check against `merlin.agent.md`:**
- The agent file does not directly discuss unarchival, but the Temporary-vs-Permanent section implies lifecycle reversibility (a temp is a temp regardless of dispatch count). The skill makes the reversal explicit without contradicting the agent file.
- "Always include clear constraints" generalizes to the Re-archival Trigger Convention's "concrete and observable" requirement.

**Expectations satisfied:** all six (date → `*(active)*` flip; Task column appended; re-archival trigger blockquote added; row stays in Temporary Agents table; tagline + File untouched; trigger is concrete).

## Eval 3 — FORGE single-dispatch archival

**Prompt:** "Temp agent FORGE just completed its single dispatch. Close them out."

**Skill-directed behaviour:**
1. **Archival Trigger Detection** → single-dispatch temp, dispatch returned, scope bounded and complete, completion signalled. All conditions met.
2. **Retain-vs-Archive Decision Table** row 1 (single-dispatch, complete) → **Archive now.** Default lifecycle.
3. **Roster Update Protocol → Archiving a temp:**
   - Flip Archived from `*(active)*` to today's `YYYY-MM-DD`.
   - No re-archival trigger blockquote to remove (single-dispatch temps don't have one — that's retained-temp territory per worked example 2's DON'T clause and the Convention section).
   - `File` column unchanged.
   - Tagline callout intact.
4. **Session Checkpoint Cleanup rule** → MERLIN does not delete or edit FORGE's session-memory files.

**Cross-check against `merlin.agent.md`:**
- Direct application of "Temporary: One-time task specialists … after completion" with the File Location Convention correction (no physical move). No divergence from the source constraints.

**Expectations satisfied:** all six (single-dispatch recognized; date flip; no trigger to remove; no file move; tagline intact; session-memory untouched).

## Scope-boundary check

All three evals exercise archival/offboarding only:
- Archival trigger detection
- Retain-vs-archive classification
- Roster Archived-column flip (both directions)
- Re-archival trigger recording and removal
- File Location Convention (no moves on archive)
- Session-checkpoint cleanup boundary (MERLIN does not touch other agents' memory)
- Permanent-agent archival refusal (covered in skill body; not needed as a fourth eval because the decision-table row and worked example 3 make the behaviour unambiguous)

None of the evals require MERLIN to:
- Hire a new agent or invoke SCOOP (that is the `hire-agent` skill)
- Author a `.agent.md` file from scratch (that is the `hire-agent` skill)
- Append a new row to the Permanent Team or Temporary Agents table with Hired/Tagline columns populated (that is the `hire-agent` skill)
- Edit the persona or responsibilities of an already-active agent
- Retire a permanent team member (out of scope — requires separate user-driven workflow)
- Move agent files between `.github/agents/` and `.github/agents/temps/` (File Location Convention explicitly forbids this during archival)

Those boundaries are explicitly called out in the skill's `NOT for:` clause, the File Location Convention section, and the Permanent Agents section.

## Verdict

All three evals produce behaviour traceable to both the new `archive-agent` skill and the source `merlin.agent.md`. Archival content was extracted faithfully from Responsibility 6 and the Temporary vs Permanent section, with the File Location Convention updated to reflect current repo practice (no physical moves; Archived column is source of truth). Identity, Persona, and absolute principles (roster-always-updated, temp-vs-permanent distinction) remain referenced but the persona itself stays in the agent file. Hiring content is deliberately absent, routed to the parallel `hire-agent` skill per the P3-T5a/P3-T5b split.
