---
description: "Run an automated PROBE test run. Usage: /probe-run <run-type> [scope] [model=<slug>]. Examples: /probe-run baseline | /probe-run regression smoke | /probe-run baseline TC-021 | /probe-run baseline category D | /probe-run baseline model=gpt-4.1"
---

Delegate to PROBE. Pass the following brief to PROBE verbatim — do not summarize or reinterpret it. The invocation arguments from the user's message (run type, scope, model override) are included in the brief below as placeholders; substitute the actual values from the user's message before dispatching.

---

**Brief for PROBE:**

Load and read both of these playbooks before doing anything else:
- `.github/playbooks/run-test-plan/run-test-plan.md` — test execution protocol
- `.github/playbooks/design-test-rubric/design-test-rubric.md` — model-verification protocol (Layers 1, 2, 3)

Follow both throughout this run.

**Step 1 — Parse invocation arguments.**

Check the user's message for:
- A **run type**: `baseline`, `regression`, or any custom label — **required**
- A **scope** (optional): one of `all` (default), `smoke`, `TC-###`, or `category <X>`
- A **model override** (optional): `model=<slug>` (e.g. `model=gpt-4.1`, `model=mixed-123abc`)

If no run type was provided, stop and ask:
> What run type is this? (e.g. `baseline`, `regression`, or a custom label)

Do not proceed until a run type is confirmed.

**Step 2 — Determine the model identifier.**

- If `model=<slug>` was provided, use it as the Layer 3 result (user has already confirmed the name). Still run Layers 1 and 2 to verify observed behavior aligns.
- If no `model=` was provided, run all three layers of the model-verification protocol. I'll confirm the model indicator when you ask.

**Step 3 — Run.**

**If scope is `all` (or no scope was given):**

> **Note:** Category N (TC-084–TC-089) is excluded from `all` runs — PROBE cannot run its own protocol tests. Category N must be run separately through ARTHUR using the testing protocol at `.github/skills/orchestrate-delegation/references/testing-protocol.md`.

Do NOT dispatch PROBE once for the full suite — that will truncate. Instead:

1. Determine the report filename now: `artifacts/testing/reports/probe-{run_type}-{model}_{YYYY-MM-DD}-{seq}.md` where `{seq}` is a two-digit sequence number starting at `01` (e.g., `probe-baseline-gpt41_2026-04-26-01.md`). To determine `{seq}`, list `artifacts/testing/reports/` and find the highest existing sequence for files matching `probe-{run_type}-{model}_{YYYY-MM-DD}-*.md` on that date, then increment by 1. If none exist, use `01`. Pass this filename to every PROBE dispatch below.
2. Dispatch PROBE **sequentially**, once per category, using the brief template below. Do not start the next category until the previous one completes.
3. After category N completes, dispatch PROBE one final time with the brief: _"Finalize `{report_file}`."\_

**Per-category brief template** (substitute `{X}`, `{run_type}`, `{model}`, `{report_file}` before sending):
> Run category {X} of the test plan (`artifacts/testing/test-plan.md`). Run type: `{run_type}`. Model: `{model}`. Rubric: `v1.1.1`.
> Report file: `{report_file}`.
> - If the report file does not exist yet (category A), create it from the template at `artifacts/testing/probe-report-template.md` and write it to `artifacts/testing/reports/`. Replace all `{{PLACEHOLDER}}` values.
> - If the report file already exists (categories B–M, excluding N), append this category's results to the existing Results Table and Violation Log sections — do NOT overwrite or recreate the file.
> Follow the run-test-plan skill throughout. Clean up after every test.

Dispatch for categories: A, B, C, D, E, F, G, H, I, J, K, L, M — in that order. Skip N entirely. PROBE reads the test plan to determine which tests belong to each category; ARTHUR does not need to read the test plan.

**If scope is `smoke`, `TC-###`, or `category <X>`:**

1. Determine the report filename: `artifacts/testing/reports/probe-{run_type}-{model}_{YYYY-MM-DD}-{seq}.md` using the same sequencing logic as above. Pass this filename to the PROBE dispatch.
2. Dispatch PROBE once with this brief (substitute values before sending):

> Run {scope} of the test plan (`artifacts/testing/test-plan.md`). Run type: `{run_type}`. Model: `{model}`. Rubric: `v1.1.1`.
> Report file: `{report_file}`.
> Create the report file from the template at `artifacts/testing/probe-report-template.md` and write it to `artifacts/testing/reports/`. Replace all `{{PLACEHOLDER}}` values. Record only the tests that were run.
> Follow the run-test-plan skill throughout. Clean up after every test.

> **If scope is `category N`:** do NOT dispatch PROBE. Category N cannot be run by PROBE — it is self-referential. Redirect the user: _"Category N must be run through ARTHUR using the testing protocol at `.github/skills/orchestrate-delegation/references/testing-protocol.md`. Start a new session and ask ARTHUR to run category N."_

Tag every dispatch with the confirmed `run_type`. Read the current rubric version from the latest entry in §8 of `artifacts/testing/probe-scoring-rubric.md` and use it as the `rubric_version` value in the scorecard frontmatter.


