# P3-T5a Eval-Pass Walkthrough — `hire-agent` skill

Logical walkthrough verifying each eval prompt, when handled by MERLIN loading the `hire-agent` skill, produces behaviour that matches the skill's guidance and traces to `merlin.agent.md` — confined to hiring (archival/offboarding lives with the `archive-agent` skill).

## Eval 1 — `react-component-engineer-permanent`

**Prompt:** "We need someone who can write React components for our design system. Hire them."

**Skill-directed behaviour:**
1. **Hire-vs-No-Hire Decision Table** → roster check first. No existing agent on the Permanent Team owns React component work (QUILL is docs, PRISM is CSS, SAGE is planning, SCOOP is research). Proceed to hire.
2. **Placement Decision** → recurring capability (design-system component work is ongoing) → **permanent**. Row goes in the Permanent Team table; file at `.github/agents/<name>.agent.md`.
3. **Hiring Protocol step 3** → mandatory SCOOP invocation with the standard research brief ("competencies, mindset traits, quality markers, and anti-patterns for a top-tier React component engineer"). MERLIN waits for SCOOP's response.
4. **Steps 4–9** → reads SCOOP's findings, picks a name, drafts persona + identity + expertise + tools.
5. **Agent File Schema** → drafts the file with all eight body sections in order, including the REQUIRED `## Research Foundation` section summarizing SCOOP's actual output.
6. **Roster Update Protocol (Permanent hire)** → appends a row to the Permanent Team table with `Agent | Role | Use When | Hired (today) | Tagline` columns.
7. **"Never dispatch the agent you just hired" rule** → MERLIN announces the hire and hands back to ARTHUR. Does not issue React work to the new agent.

**Cross-check against `merlin.agent.md`:**
- Hiring Process step 2 (CALL SCOOP mandatory) → reproduced in the skill's "CALL SCOOP (mandatory)" step 3 and enforced in every eval.
- "agent file MUST include a `## Research Foundation` section" → reproduced verbatim in the Agent File Schema's body section 3.
- Constraint "Do NOT perform the tasks that hired agents are meant to do" → reproduced in the "Never dispatch the agent you just hired" rule.

**Expectations satisfied:** all six (roster check first; SCOOP before drafting; `## Research Foundation` from SCOOP output; permanent placement; roster row same turn; no dispatch of the new agent).

## Eval 2 — `one-shot-python-migration-temp`

**Prompt:** "Hire a temp to run a one-shot Python migration script for converting legacy config files. This is a single-task hire."

**Skill-directed behaviour:**
1. **Placement Decision** → one-shot task with specialized skill set → **temporary**. Single-dispatch, not retained.
2. **Hiring Protocol** → SCOOP invocation is still mandatory. Temp status does not waive research.
3. **Placement table** → active-file location is `.github/agents/<name>.agent.md` (NOT `temps/`). The `temps/` path is only for archived agents; moving there is the `archive-agent` skill's job.
4. **Roster Update Protocol (Temporary hire)** → row in the Temporary Agents table with `Agent | Role | Task | Hired | Archived | File`. Hired = today. Archived = `*(active)*`. File = `.github/agents/<name>.agent.md`. Tagline recorded in the callout below the table.
5. **Retained-vs-single-dispatch rule** → the prompt explicitly says "single-task hire." No re-archival trigger callout is added. Re-archival triggers are only for retained temps (SPLICE pattern).
6. **Scope boundary** → MERLIN does NOT archive the file in this turn. Archival is out of scope for this skill and routes to `archive-agent`.

**Cross-check against `merlin.agent.md`:**
- "Temporary: One-time task specialists → created in `.github/agents/`, moved to `.github/agents/temps/` after completion" → reproduced in the Placement Decision table (active vs archive locations).
- Constraint "Do NOT create agents without updating the roster" → enforced in expectation #2 (row added to Temporary Agents table same turn).

**Expectations satisfied:** all six (SCOOP before drafting; temp placement; active-location file path; `*(active)*` Archived column; no re-archival trigger; no archival work performed).

## Eval 3 — `declined-hire-existing-coverage`

**Prompt:** "The team needs a CSS specialist to own styling across the project long-term."

**Skill-directed behaviour:**
1. **Hire-vs-No-Hire Decision Table**, row 1 → "Existing agent's responsibilities already cover the task." PRISM is on the Permanent Team roster with Use-When "Writing or reviewing CSS, designing token systems, building responsive layouts…" (hired 2026-04-18). This is a direct match.
2. **Decline the hire.** Name PRISM. Recommend engaging PRISM directly.
3. **No SCOOP invocation** — no hire to research. Step 3 of the Hiring Protocol is only reached after the hire-vs-no-hire check decides "hire."
4. **No agent file created**, **no roster row added**.
5. **"Ambiguous requirement" fallback** — if the user pushes back and insists on a new hire anyway, MERLIN asks for the specific gap PRISM does not cover (Hire-vs-No-Hire Decision Table's "Requirement is ambiguous" row: "Ask for clarification before invoking SCOOP. Do not hire against vague intent.").

**Cross-check against `merlin.agent.md`:**
- The agent file does not explicitly discuss declining hires, but its Constraints section ("Do NOT perform the tasks that hired agents are meant to do") and the overall "hire only when needed" intent of the Hiring Process imply that redundant hires are out of bounds. The skill's Hire-vs-No-Hire Decision Table makes this implicit rule explicit — a legitimate extension, not a contradiction.
- Constraint "Do NOT read individual agent `.agent.md` files to understand the team — the team roster has everything you need" → reproduced in spirit: the roster check is the source of truth for "does this agent already exist?"

**Expectations satisfied:** all six (roster consulted; PRISM named as existing coverage; hire declined; no SCOOP call; no agent file; no roster change; clarification path if user pushes back).

## Scope-boundary check

All three evals exercise hiring only:
- Hire-vs-no-hire decision
- SCOOP skills-research integration
- Agent file authoring (schema, required `## Research Foundation`)
- Permanent vs temporary placement
- Single-dispatch vs retained temp
- Roster update (Permanent Team vs Temporary Agents tables)
- Declining redundant hires

None of the evals require MERLIN to:
- Offboard or archive agents (that is the `archive-agent` skill)
- Update the Archived column from `*(active)*` to a real date
- Move files from `.github/agents/` to `.github/agents/temps/`
- Edit an existing agent's identity, persona, or responsibilities after hire
- Clean up session checkpoint files for departing agents
- Dispatch the new agent to perform work (that is ARTHUR's job)
- Re-derive MERLIN's own process philosophically

Those boundaries are explicitly called out in the skill's `NOT for:` clause and the "Never dispatch the agent you just hired" rule.

## Verdict

All three evals produce behaviour traceable to both the new `hire-agent` skill and the source `merlin.agent.md`. Hiring content was extracted faithfully (Hiring Process → Hiring Protocol, Agent File Requirements → Agent File Schema, Temporary vs Permanent → Placement Decision, plus a new explicit Hire-vs-No-Hire Decision Table derived from the agent file's implicit rules). Identity, Persona, and absolute principles (SCOOP-first, Research-Foundation-required, roster-always-updated, never-dispatch-own-hire) remain referenced but the persona itself stays in the agent file. Archive/offboarding content is deliberately absent, routed to the parallel `archive-agent` skill per the P3-T5a/P3-T5b split.
