# P3-T2b Eval-Pass Walkthrough — `create-plan` skill

Logical walkthrough verifying that each eval prompt, when handled by SAGE loading the `create-plan` skill, produces behaviour that matches both the skill's guidance and the source `sage.agent.md`.

## Eval 1 — `plan-from-approved-spec`

**Prompt:** "The spec at artifacts/spec007-recurring-exports/spec.md has been approved at the Spec Checkpoint. Produce the implementation plan."

**Skill-directed behaviour:**
1. Confirm path — approved spec + Plan Checkpoint next → full-path continuation, plan is the correct artifact (SKILL.md "When a plan is the right output" table, row 1).
2. Planning Protocol step 1 → dispatch SCOOP for codebase/pattern research (scheduler patterns, email-delivery module, existing export code).
3. Step 2 → web-verify any external library behaviour (e.g., cron/scheduler semantics) as needed.
4. Step 3 → consider edge cases (DST, missed runs, quota exhaustion) for Watch Out.
5. Step 4 → draft Summary, then phases using `.github/templates/plan-template.md` structure. Foundational types / schema in Phase 1; parallel feature work in Phase 2–3; integration in Phase 4. Each phase carries `PARALLEL:` and `BLOCKED BY:` annotations; per-task `Depends on:` lines where specific prerequisites apply; every task names explicit file paths with no in-phase overlap.
6. Step 5 → if the task count exceeds ~10 or the work spans multiple sessions, also produce `tasks.md`.
7. `create_file` writes `artifacts/spec007-recurring-exports/plan.md` (and `tasks.md` if the split rule fires).
8. Report back with folder path, files written, phase summary, Open Questions count, Watch Out pointer. Stop.

**Cross-check against `sage.agent.md`:**
- Planning Protocol step 1 ("Research via SCOOP") → matches skill's Planning Protocol step 1.
- "Plan Output Format" section (Summary / Phases / Watch Out / Open Questions) → matches Required Plan Structure.
- "Every phase MUST include an explicit parallelization annotation … a BLOCKED BY annotation … Per-task Depends on lines" → directly preserved in skill's Dependency Annotation Rules.
- "Every task explicitly lists which files it creates or modifies" and "Tasks within the same phase MUST NOT touch overlapping files" → preserved in File Assignment Rules.
- "For plans with more than ~10 tasks or work expected to span multiple sessions, also produce a separate `tasks.md`" → preserved verbatim intent in tasks.md Split Rule.
- "Always write artifacts to disk using `create_file` — never return artifact content as response text" → preserved in Plan Checkpoint handoff and "narration is not delivery" rule.

**Expectations satisfied:** all five.

## Eval 2 — `plan-standard-path-no-spec`

**Prompt:** "Standard path: rename the existing `UserService.fetchById` method to `UserService.findById` across the backend and update all call sites and tests."

**Skill-directed behaviour:**
1. "When a plan is the right output" decision table — multi-file change with clear intent, no new surface area → **standard path, plan, no spec**.
2. Planning Protocol step 1 → SCOOP identifies call sites and test coverage.
3. Planning Protocol step 5 ("Right-size") → a symbol rename does not get five phases or a `tasks.md`. Likely a one- or two-phase plan.
4. File Assignment Rules → every task names specific file paths (service file, call-site files, test files); no vague "update the service module".
5. Watch Out surfaces at least one non-obvious risk: string-based references, reflection / serialized property names, shadowed identifiers, documentation drift.
6. `create_file` writes `artifacts/spec###-<short-name>/plan.md`. Report back and stop. No `tasks.md`.

**Cross-check against `sage.agent.md`:**
- "Right-size your output. A 2-file task doesn't need 5 phases" → preserved in Planning Protocol step 5 and Example 3.
- "Do NOT leave file assignments vague — every task must name specific files" → preserved in File Assignment Rules and "Rule: vague file assignments are not assignments".
- "Do NOT skip the 'Watch Out' section — it's what separates a plan from a wish list" → preserved in Required Plan Structure and Plan Checkpoint handoff.

**Expectations satisfied:** all five.

## Eval 3 — `plan-hidden-file-conflict`

**Prompt:** "Draft a plan for adding a new `validateCart()` helper to `apps/api/checkout.ts` while also refactoring `apps/api/checkout.ts` to use the new `PricingEngine` module."

**Skill-directed behaviour:**
1. File Assignment Rules → both tasks touch `apps/api/checkout.ts`. "Tasks within the same phase MUST NOT touch overlapping files" → sequence them.
2. Phase 1 adds `validateCart()`; Phase 2 refactors to `PricingEngine` with `Depends on: Task 1.1`.
3. `PARALLEL:` annotation never groups the two tasks. If other unrelated foundational work exists, that work may be parallel within its phase — but the checkout.ts pair is sequential.
4. Watch Out explicitly calls out the `checkout.ts` co-ownership risk and why ordering matters (merge conflicts, refactor-over-incomplete-helper, test breakage).
5. `create_file` writes the plan. SAGE stops at the Plan Checkpoint.

**Cross-check against `sage.agent.md`:**
- "Tasks within the same phase MUST NOT touch overlapping files. If two tasks need the same file, they go in sequential phases" → preserved verbatim in File Assignment Rules. Example 2 in the skill dramatizes this exact scenario.
- "Watch Out — The traps, gotchas, subtle dependencies, and edge cases that would derail implementation" → preserved in Required Plan Structure.
- "Task-level dependencies: annotate with `Depends on: Task X.Y` when only specific tasks are prerequisites" → preserved in Dependency Annotation Rules.

**Expectations satisfied:** all five.

## Verdict

All three evals produce behaviour that is traceable to both the new `create-plan` skill and the source `sage.agent.md`. Plan-authoring content was extracted faithfully; spec-authoring content was left to the parallel `create-spec` dispatch and is not duplicated here.
