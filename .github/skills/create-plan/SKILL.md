---
name: create-plan
description: Implementation-plan authoring playbook for SAGE — the how-to for turning an approved spec (or a clear standard-path request) into a phased, dependency-annotated plan an implementer can execute without further clarification. Use this skill whenever SAGE is asked to produce a plan, whenever ARTHUR routes work down the standard path, whenever a spec has been approved at the Spec Checkpoint, whenever work must be decomposed into phases with PARALLEL / BLOCKED BY / Depends on annotations, or whenever a multi-file or multi-agent effort needs explicit file-ownership and sequencing before dispatch. NOT for: writing feature specifications (use the create-spec skill), research-only requests (route to SCOOP), code or documentation implementation (SAGE does not implement), or identity/persona questions about SAGE (those live in the agent file).
---

# Create a Plan

Process detail for SAGE when the deliverable is an implementation plan. The agent file defines *who SAGE is* and the non-negotiable principles; this skill defines *how SAGE turns an approved spec (or a clear standard-path request) into an executable plan* — phase design, dependency annotation, file-ownership assignment, and checkpoint handoff.

Read this skill whenever SAGE is about to write a `plan.md`. If you are SAGE and the task is "create a plan," or you are on the full path after a spec has been approved, or on the standard path from the start, you should already be inside this skill. Spec authoring — intent capture, user scenarios, functional requirements — is a separate deliverable covered by the `create-spec` skill. Do not blend the two.

## How to use this skill

1. **Confirm the path** — a plan is a standard- or full-path artifact. On the full path, the spec must already be approved at the Spec Checkpoint.
2. **Research via SCOOP** before designing phases.
3. **Verify** external library and API behaviour with web search.
4. **Design phases** — dependency-ordered, with explicit parallel / blocked-by annotations.
5. **Assign files** — every task names the specific files it owns; no two parallel tasks share a file.
6. **Right-size** — a two-file task does not need five phases.
7. **Checkpoint** after each major phase is drafted.
8. **Write the artifact to disk** with `create_file`. Never return plan content as response text.
9. **Hand off** at the Plan Checkpoint — report file path, phase summary, open questions. Then stop.

---

## When a plan is the right output

| Situation | Plan needed? |
|-----------|--------------|
| Spec was approved at the Spec Checkpoint (full path) | **Yes** — this is the next artifact |
| User explicitly said "plan this" / "standard path" | **Yes** |
| Multi-file change with clear intent and no new surface area | **Yes** — standard path, no spec |
| Work spans multiple agents or needs ordering to avoid conflicts | **Yes** |
| Research-only ("investigate", "compare", "look into") | **No** — route to SCOOP |
| Net-new feature, migration, rewrite with ambiguous scope | **No** — write a spec first via the `create-spec` skill |
| One-file fix, bug patch, obvious edit | **No** — no plan, no spec |

### Rule: explicit path requests are binding

If the user or ARTHUR named the standard or full path, produce a plan. If the full path was named, the spec comes first; do not skip straight to a plan.

---

## Planning Protocol

Five steps. Do not reorder. Do not merge steps.

1. **Research first (via SCOOP).** Before drafting phases, delegate technical research to SCOOP through the agent tool: codebase patterns, existing module boundaries, API shapes, known gotchas. You read SCOOP's findings; you do not read the codebase yourself. SCOOP is the research expert — use the subagent.
2. **Verify externalities.** If the plan depends on external libraries, APIs, or platform behaviour, use web search to confirm current documentation. Training knowledge is in the past; the docs are in the present.
3. **Consider edge cases and implicit requirements** the user or spec did not mention. These feed the **Watch Out** section.
4. **Plan — WHAT, not HOW.** Describe what each task must achieve and which files it touches. Do not write pseudocode, do not dictate function signatures, do not prescribe algorithms. The implementer is the expert on implementation.
5. **Right-size the output.** A 2-file change does not need 5 phases. Match plan complexity to task complexity. Produce a separate `tasks.md` or detailed per-task annotations only when the work genuinely warrants it (see tasks.md split rule below).

   **Phase size rule:** Each phase must be completable by a single agent in a single pass. If a phase contains more than ~8 tasks, or if executing all tasks would produce more than ~200 lines of file output, **split the phase**. An agent that hits its output token limit mid-phase leaves the file in an inconsistent half-written state — phased splitting prevents this. Each sub-phase should have a clear entry criterion (what the prior sub-phase produced) and a clear exit criterion (what the next sub-phase needs as input).

   **Flag to ARTHUR** when a task or phase is ambiguously large — e.g., "Author 22 test entries" is not one task, it is many. Split it during planning, not during execution.

### Rule: plans describe outcomes, not keystrokes

A plan that tells the implementer "write a function `foo(x: int) -> str` that does X on line 42" has overreached. Name the outcome, name the file, name the dependency — let the implementer decide the shape of the code.

---

## Required Plan Structure

Use `.github/templates/plan-template.md` as the starting structure. Every plan MUST include these sections, in order:

### Summary
One paragraph: what is being built, the primary technical approach, and the key constraint.

### Phases
Dependency-ordered phases. Each phase contains tasks, and each task explicitly names its files and dependencies:

```
## Phase 1: [Name] — [Purpose]
- Task 1.1: [Description] → [Agent role]
  Files: [explicit file paths]
- Task 1.2: [Description] → [Agent role]
  Files: [explicit file paths]
> PARALLEL: Tasks 1.1 and 1.2 run simultaneously (no file overlap)

## Phase 2: [Name] — [Purpose]
- Task 2.1: [Description] → [Agent role]
  Files: [explicit file paths]
  Depends on: Task 1.1
- Task 2.2: [Description] → [Agent role]
  Files: [explicit file paths]
  Depends on: Task 1.1, Task 1.2
> PARALLEL: Tasks 2.1 and 2.2 run simultaneously
> BLOCKED BY: Phase 1 (all tasks)
```

Every phase MUST include:
- An explicit **parallelization annotation** stating which tasks run in parallel and which are sequential.
- A **`BLOCKED BY:`** annotation listing the prior phases or tasks that must complete first.
- Per-task **`Depends on:`** lines when a task depends on specific prior tasks rather than an entire phase.

### Watch Out
The traps, gotchas, subtle dependencies, and edge cases that would derail implementation if nobody thought about them first. This section is non-negotiable — a plan without Watch Out is incomplete.

### Open Questions
Uncertainties or decisions that need user input before execution. If you have none, say "None" explicitly. Never hide them.

---

## Dependency Annotation Rules

Dependencies are the backbone of the plan. Get them explicit, or phased execution will break.

- **Phase-level dependency.** Use `> BLOCKED BY: Phase N` when an entire phase must complete before this one can start.
- **Task-level dependency.** Use `Depends on: Task X.Y` when only a specific prior task is a prerequisite — not the whole phase. This unlocks earlier execution for tasks that would otherwise be idle.
- **Parallel annotation.** Every phase states either `PARALLEL: Tasks A, B, C run simultaneously (no file overlap)` or notes that tasks within the phase are sequential with reasons.
- **Cross-cutting dependencies.** Shared config, types, schemas, or migrations that multiple downstream tasks need become **foundational tasks in Phase 1**.
- **If in doubt, sequence it.** A false parallel annotation produces merge conflicts. A false sequential annotation only wastes wall-clock time. Err on the side of sequencing.

### Rule: a `Depends on:` list is a promise

If Task 2.1 is annotated `Depends on: Task 1.1`, then Task 2.1 must not read, write, or assume anything produced by Task 1.2. Violating that promise is how plans quietly become wrong.

---

## File Assignment Rules

Every task owns the files it touches. Ownership is the contract that makes parallel execution safe.

- **Every task lists the specific files it creates or modifies.** No vague "update the auth module". Name the paths.
- **Tasks within the same phase MUST NOT touch overlapping files.** If two tasks need the same file, they go in sequential phases — period.
- **One owner per file per phase.** If `types.ts` needs contributions from two tasks, either merge them into one task or split them across phases.
- **Shared files (schemas, types, config) become Phase 1 foundational tasks.** Downstream tasks consume; they do not co-author.
- **Cross-phase file reuse is fine** as long as the later task is annotated `Depends on:` the earlier one.

### Rule: vague file assignments are not assignments

"Modifies the checkout flow" is not a file assignment. `apps/web/src/checkout/index.tsx, apps/web/src/checkout/validation.ts` is a file assignment. If you cannot name the paths, do more research before writing the phase.

---

## tasks.md Split Rule

**Do not produce `tasks.md`.** Every plan uses the embedded checkboxes in `plan.md` as the single source of truth for task tracking.

A separate `tasks.md` creates a second artifact that must stay in sync with `plan.md`. Because all execution dispatches target `plan.md`, `tasks.md` will always drift — adding maintenance cost with no operational benefit.

### Rule: plan.md is the only tracker

All task checkboxes live in `plan.md`. Agents update `plan.md` checkboxes as tasks complete. No secondary tracker is needed, regardless of task count or session span.

---

## Plan Checkpoint — Handoff Expectations

After the plan is written, ARTHUR runs the Plan Checkpoint before any phased execution begins. SAGE's responsibility is to make that checkpoint possible:

1. **Write the file to disk** with `create_file`. Path: `artifacts/spec###-short-name/plan.md`. Never return plan content as response text.
2. **Report back** to ARTHUR in this exact shape:
   - The spec folder path
   - The file(s) written (`plan.md`, optionally `tasks.md`)
   - A 1–2 sentence summary of the plan shape: phase count, parallel vs sequential balance, agents involved
   - The count of Open Questions (so ARTHUR knows to surface them) and a pointer to the Watch Out section
3. **Stop.** Do not start executing phases. Do not dispatch agents. The user owns the checkpoint decision.

### Rule: narration is not delivery

A plan that exists only in your response text did not get written. Every plan deliverable must include an actual `create_file` tool call. If you catch yourself describing plan contents in prose without a file-write tool call alongside it, stop and emit the tool call.

---

## Artifact Location

Plans live in numbered spec folders under `artifacts/`:

1. **ARTHUR assigns the folder name.** On the full path, use the same folder where the approved spec was written (e.g., `artifacts/spec004-fix-payment-timeout/`).
2. **On the standard path with no pre-existing folder**, scan `artifacts/` for the highest existing `spec###-*`, increment, and use the provided short name (or `spec###-unnamed` flagged for ARTHUR to rename).
3. **`create_file` creates missing parent directories automatically.** Do not run a separate mkdir step. Do not ask the user for permission — just write.
4. **The only filename is `plan.md`.**

---

## Session Resumption

Plans span multiple phases; checkpoint as you go.

- **Before starting:** check `/memories/session/` (or `.agent-memory/session/` in memory-less mode) for a prior checkpoint on this plan. If found, resume from the next incomplete phase rather than starting over.
- **While working:** after drafting each phase (and after identifying Watch Out entries), write a checkpoint recording: target spec folder, current stage, phases drafted so far, key dependency decisions, and any open questions surfaced.
- **After completing:** clear the checkpoint.

See `AGENTS.md` for the full Session Resumption Protocol.

---

## Worked examples

### Example 1 — Parallel annotation with no file overlap

**DO:**

> Plan has Phase 2 with three tasks: T2.1 edits `apps/api/auth.ts`, T2.2 edits `apps/api/billing.ts`, T2.3 edits `apps/web/README.md`. No shared files. SAGE annotates:
>
> > `> PARALLEL: Tasks 2.1, 2.2, 2.3 run simultaneously (no file overlap)`
> > `> BLOCKED BY: Phase 1 (shared types in apps/api/types.ts)`
>
> ARTHUR can dispatch all three in a single batched response.

**DON'T:**

> SAGE writes Phase 2 as three tasks with no `PARALLEL:` annotation and no `BLOCKED BY:` annotation, assuming "ARTHUR will figure it out."
>
> Wrong. Missing annotations force ARTHUR to guess at dependency order, which means ARTHUR guesses wrong and either serializes independent work or parallelizes conflicting work. Every phase needs explicit annotations — they are the contract between plan and execution.

---

### Example 2 — File conflict hidden inside a parallel phase

**DO:**

> Draft has T3.1 ("add `validateCart()` to `checkout.ts`") and T3.2 ("refactor `checkout.ts` to use new pricing engine"). Both touch `checkout.ts`. SAGE splits them:
>
> > Phase 3: T3.1 (add `validateCart()`)
> > Phase 4: T4.1 (refactor to pricing engine) — `Depends on: Task 3.1`
>
> Sequential, safe, explicit.

**DON'T:**

> SAGE keeps both in Phase 3 and annotates `PARALLEL: Tasks 3.1 and 3.2`. Parallel execution produces merge conflicts in `checkout.ts`.
>
> Wrong. Tasks within a phase MUST NOT touch overlapping files. Two tasks needing the same file belong in sequential phases. The parallel annotation is a promise of file-independence — breaking it produces broken merges.

---

### Example 3 — Over-phasing a trivial change

**DO:**

> User: "Rename `getUser()` to `fetchUser()` across the codebase."
>
> SAGE produces a one-phase plan with a single task: "Rename `getUser` → `fetchUser` repo-wide. Files: all `.ts` / `.tsx` files containing the symbol (implementer uses workspace rename)." No `tasks.md`. No five-phase ceremony.

**DON'T:**

> SAGE produces Phase 1 (research), Phase 2 (plan), Phase 3 (rename in module A), Phase 4 (rename in module B), Phase 5 (test). Five phases, a `tasks.md`, and a Watch Out section for a symbol rename.
>
> Wrong. Right-size the plan. A 1-file-pattern change gets a 1-phase plan. Over-phasing burns tokens and hides the simple shape of the work.

---

### Example 4 — Plan Checkpoint handoff

**DO:**

> SAGE writes `artifacts/spec007-recurring-exports/plan.md` with `create_file`, then reports:
>
> > Plan written to `artifacts/spec007-recurring-exports/plan.md`. 4 phases: Phase 1 foundational (shared types, scheduler schema), Phases 2–3 parallel feature work, Phase 4 integration. 14 tasks total — `tasks.md` also produced. **1 Open Question** (email-delivery provider choice). Watch Out covers DST scheduling edge case.
>
> Stops. Does not dispatch agents.

**DON'T:**

> SAGE: "Plan written. Starting Phase 1 now — dispatching agent for foundational types."
>
> Wrong on two counts. First, SAGE does not dispatch agents — ARTHUR does. Second, the Plan Checkpoint is a hard stop; phased execution does not start until the user approves the plan. No exceptions.

---

## Quick reference

- **Is a plan the right output?** → Check the decision table. Standard or full path (post-Spec-Checkpoint) only.
- **Research before designing phases?** → Always. SCOOP first; never read the codebase yourself.
- **Every phase annotated?** → `PARALLEL:` and `BLOCKED BY:` are non-negotiable.
- **Every task has files?** → Explicit paths, no overlap within a phase.
- **Watch Out filled in?** → Non-negotiable.
- **Open Questions surfaced?** → Explicit section, never hidden. "None" is a valid answer; silence is not.
- **tasks.md needed?** → Only if >10 tasks or multi-session work.
- **Written to disk?** → `create_file` always. Narration is not delivery.
- **Checkpoint handoff?** → Report folder, files, phase summary, Open-Questions count, Watch Out pointer. Then stop.
