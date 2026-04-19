# P3-T2a Eval-Pass Walkthrough — `create-spec` skill

Logical walkthrough verifying that each eval prompt, when handled by SAGE loading the `create-spec` skill, produces behaviour that matches both the skill's guidance and the source `sage.agent.md`.

## Eval 1 — `spec-new-feature`

**Prompt:** "Create a spec for a feature that lets users schedule recurring exports of their account data (daily/weekly/monthly) with email delivery."

**Skill-directed behaviour:**
1. Confirm path — explicit "Create a spec" → full-path artifact (SKILL.md "When a spec is the right output" table, row 1).
2. Spec Authoring Protocol step 1 → dispatch SCOOP for research on existing export/scheduler/email patterns.
3. Step 3 → capture intent: "Users can schedule data exports on a recurring cadence; system delivers the generated export to a registered email address."
4. Step 4 → outline P1 (schedule creation), P2 (delivery + retry), P3 optional (schedule management UI).
5. Step 5 → draft full spec using `.github/templates/spec-template.md` structure.
6. `create_file` writes `artifacts/spec###-recurring-exports/spec.md`.
7. Report back with folder path, file written, summary, Open-Questions count. Stop.

**Cross-check against `sage.agent.md`:**
- Planning Protocol step 1 ("Research via SCOOP") → matches skill's Authoring Protocol step 1.
- "Specification Output Format" (Overview / User Scenarios / Requirements / Success Criteria / Edge Cases) → matches Required Spec Structure.
- "Always write artifacts to disk using `create_file` — never return artifact content as response text" → matches "Rule: narration is not delivery".
- "After writing, confirm back to the orchestrator: the spec folder path, the file(s) written, and a brief 1–2 sentence summary" → matches Spec Checkpoint handoff report shape.

**Expectations satisfied:** all five.

## Eval 2 — `spec-ambiguous-request`

**Prompt:** "I want a way for my users to 'collaborate better'. Create a spec for it."

**Skill-directed behaviour:**
1. Spec Authoring Protocol step 3 ("Capture intent") → restate: "User wants some form of collaboration feature, but the category is unspecified (comments? shared editing? notifications? @mentions?)."
2. "Rule: intent first, structure second" → ambiguity detected. Either ask the user or capture in Open Questions.
3. If drafting proceeds, Open Questions section lists concrete sub-questions. Spec Checkpoint handoff flags the count.
4. Does not invent scope.

**Cross-check against `sage.agent.md`:**
- "Consider — Identify edge cases, error states, and implicit requirements the user didn't mention" and "Open Questions — Uncertainties or decisions that need user input before proceeding. Don't hide them — surface them clearly" → matches skill guidance to make Open Questions explicit.

**Expectations satisfied:** all five.

## Eval 3 — `spec-wrong-path`

**Prompt:** "Create a spec comparing Postgres vs MySQL for our workload."

**Skill-directed behaviour:**
1. "When a spec is the right output" decision table, research-only row → "No — route to SCOOP".
2. SAGE declines to produce a spec.md and recommends SCOOP.
3. Offers a follow-up path: once research lands, a migration spec is possible if a choice is made.
4. No `artifacts/spec###-*/` folder is created.

**Cross-check against `sage.agent.md`:**
- The agent file does not explicitly forbid mis-routed specs, but the skill's decision table operationalizes the implicit guidance: specs are for *building something*, and the agent's constraints list includes "Do NOT write code or implementation files — you are a planner, not an implementer," which underscores that specs are build-intent artifacts, not research outputs.
- SAGE's `agents: [SCOOP]` frontmatter grants the ability to redirect/recommend SCOOP routing.

**Expectations satisfied:** all five.

## Verdict

All three evals produce behaviour that is traceable to both the new `create-spec` skill and the source `sage.agent.md`. Spec-authoring content was extracted faithfully; plan-authoring content was left intact for the parallel `create-plan` dispatch.
