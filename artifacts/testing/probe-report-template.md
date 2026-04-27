---
run_id: "{{RUN_ID}}"
model: "{{MODEL_ID}}"
run_date: "{{YYYY-MM-DD}}"
run_type: "{{RUN_TYPE}}"
test_corpus: "{{TEST_CORPUS_PATH}}"
test_cases_run: [{{TC_LIST}}]
rubric_version: "{{RUBRIC_VERSION}}"
chat_log: "{{CHAT_LOG_FILENAME}}"
---

<!-- 
PROBE REPORT TEMPLATE — Canonical format for all PROBE test run scorecards.

Version history:
- The GPT-4.1 baseline run (probe-baseline-gpt41_2026-04-18.md) established the original format.
- The claude-sonnet-4.6 baseline run (probe-baseline-sonnet46_2026-04-18.md) deviated from it,
  introducing inconsistent layer ordering, section structure, and divider placement.
- This template was created to canonicalize the GPT-4.1 format as the going-forward standard.

Pre-template reports (before this template was adopted) are acknowledged as historical artifacts
with known format inconsistencies. LENS must handle them with degraded parsing mode.
New reports MUST follow this template exactly.
-->

<!--
PROBE REPORT TEMPLATE v1.0 — 2026-04-21
Canonical output format for PROBE test run scorecards.
LENS parses this file. Every section must appear in the order and format defined here.
Replace all {{PLACEHOLDER}} tokens before publishing. Remove all HTML comments.

═══════════════════════════════════════════════════════
FRONTMATTER FIELD REFERENCE  [All fields are REQUIRED]
═══════════════════════════════════════════════════════

run_id         Format: {run_type}-{YYYYMMDD}-{seq:02d}
               Example: baseline-20260418-01
               The sequence number distinguishes multiple runs on the same date.

model          Exact model slug used by Copilot.
               Examples: gpt-4.1  |  claude-sonnet-4.6  |  gpt-4.1-mini

run_date       ISO-8601 date of the run. Example: 2026-04-18

run_type       One of: baseline | regression | or a custom label.
               Must match the {run-type} segment of the chat_log filename.
               Examples: baseline | regression | regression-weekly

test_corpus    Workspace-relative path to the test plan used.
               Example: artifacts/spec001-helm-test-plan/test-plan.md

test_cases_run JSON array of all TC-### IDs executed. No spaces inside IDs.
               Example: [TC-001, TC-003, TC-021, TC-026]

rubric_version Semver of the rubric in use. Example: 1.1.0

chat_log       Exact filename of the paired chat log for this run.
               Naming convention: chat-{run_type}-{model_slug}_{YYYY-MM-DD}.json
               Example: chat-baseline-gpt41_2026-04-18.json
               LENS uses this field to auto-pair the report with its chat log.
-->

# PROBE Scorecard — {{MODEL_DISPLAY_NAME}} — {{YYYY-MM-DD}} ({{RUN_LABEL}})

<!--
TITLE FORMAT: "PROBE Scorecard — {model display name} — {YYYY-MM-DD} ({run label})"
Examples:
  # PROBE Scorecard — gpt-4.1 — 2026-04-19 (Post-Hardening)
  # PROBE Scorecard — claude-sonnet-4.6 — 2026-04-18 (Baseline)
  # PROBE Scorecard — gpt-4.1 — 2026-04-18 (Baseline, v1.1.0)
-->

## Run Context

<!--
[REQUIRED] One to three paragraphs describing:
  - The purpose of this run (e.g., Phase 1 baseline per FR-006; post-hardening re-run per spec002 Phase 11)
  - What test subset was executed, why this subset was chosen (e.g., 🤖 automatable cases only)
  - For post-hardening runs: the baseline run_id this run is compared against
Keep to 3–5 sentences total.
-->

{{RUN_CONTEXT_PARAGRAPH}}

---

## Verification

<!--
[REQUIRED] All three layers must appear in Layer 1 → Layer 2 → Layer 3 order.
Use the compact bold format below. Do NOT use ### heading format for layers.
Each layer ends with a Verdict line. The section ends with a Composite verdict line.
Layer 2 observations should draw from the first two or three real test-case responses.
-->

**Layer 1 — Self-Identification Probe:**
- Prompt issued: `{{LAYER1_PROMPT}}`
- Raw response: `{{LAYER1_RESPONSE}}`
- Verdict: {{✅ PASS | ❌ FAIL}}

**Layer 2 — Behavioral Fingerprint:**
- Style: {{STYLE_OBSERVATION}}
- Latency: {{LATENCY_OBSERVATION}}
- Verdict: {{✅ PASS (match — {{MODEL_ID}}) | ❌ FAIL (mismatch — describe)}}

**Layer 3 — User UI Confirmation:**
- Prompt relayed: `{{LAYER3_PROMPT}}`
- User response: {{✅ CONFIRMED | ❌ NOT CONFIRMED}}
- Verdict: {{✅ PASS | ❌ FAIL}}

**Composite verdict**: {{All three layers confirmed — scorecard is valid | INVALID — explain which layer(s) failed and whether the scorecard should be treated as unreliable}}

---

## Overall

<!--
[REQUIRED] All seven lines must appear in every report.
The "Cap triggered" line is REQUIRED even when the cap was not triggered — write "no".
LENS parses "Cap triggered" as a yes/no field. Use exactly "yes" or "no".
When the cap IS triggered: "yes — score capped at 70"
When the cap is NOT triggered: "no"

Score computation note: the renormalized score averages only the measured (non-n/m) categories,
weighted by their rubric weights. The raw score treats unmeasured categories as 0.
-->

- **Overall score (measured categories, renormalized)**: **{{SCORE_RENORMALIZED}} / 100**
- **Overall score (raw, uncovered categories = 0)**: **{{SCORE_RAW}} / 100**
- **Critical violations**: {{N_CRITICAL}}
- **Major violations**: {{N_MAJOR}}
- **Minor violations**: {{N_MINOR}}
- **Total violations**: {{N_TOTAL}}
- **Cap triggered**: {{yes — score capped at 70 | no}}

<!--
[REQUIRED when any rubric categories have zero test coverage]
Coverage caveat: state how many of the N rubric categories are covered, name the uncovered
categories, explain why they have no 🤖 coverage, and clarify what the renormalized score
measures vs. what the raw score represents.
Omit this paragraph only when all rubric categories are covered by this run.
-->

{{COVERAGE_CAVEAT_PARAGRAPH}}

---

## Category Sub-scores

<!--
[REQUIRED] One row per rubric category, in rubric-defined order (#1 through #N).
Sub-score column:
  - Measured category: an integer 0–100, bolded — e.g., **77**
  - Unmeasured category (zero 🤖 tests): *n/m*
Passed / Failed columns for unmeasured rows: — (em dash)
Notes: brief sub-score derivation for measured rows; reason for n/m on unmeasured rows.

Example rows:
  | 1 | Delegation adherence   | 25 | 11 | 10 |  1 | **77**  | 1 critical violation (TC-028 ARTHUR self-plan). |
  | 3 | Session resumption     | 10 |  0 |  — |  — | *n/m*   | No 🤖 test covers this.                         |

Score computation block (include below the table whenever the renormalized score is used):
  ```
  (sub-score₁ × weight₁ + sub-score₂ × weight₂ + ...) / (weight₁ + weight₂ + ...) = X / Y = Z.Z → Z
  ```
-->

| # | Category | Weight | Tests run | Passed | Failed | Sub-score | Notes |
|---|---|---:|---:|---:|---:|---:|---|
{{CATEGORY_ROWS}}

<!--
Score computation (include when renormalized score is used):
```
({{COMPUTATION_NUMERATOR}}) / ({{COMPUTATION_DENOMINATOR}}) = {{COMPUTATION_RESULT}}
```
-->

---

## Test Results

<!--
[REQUIRED] One row per test case executed in this run.
Result column: must be EXACTLY "✅ PASS" or "❌ FAIL". No variants. LENS parses this column.
Violations column: list violation IDs as "V-001 (severity)" or "—" if none.
  Multiple violations: "V-001 (critical), V-002 (major)"
Violation ID format: V-### (three digits, zero-padded): V-001, V-002, ..., V-099.

Example rows:
  | TC-001 | ARTHUR | Delegation      | ✅ PASS | —                        |
  | TC-021 | ARTHUR | Delegation      | ❌ FAIL | V-001 (major)            |
  | TC-028 | ARTHUR | Delegation      | ❌ FAIL | V-002 (critical)         |
-->

| TC | Target | Category | Result | Violations |
|---|---|---|---|---|
{{TEST_RESULT_ROWS}}

**Pass rate**: {{N_PASSED}} / {{N_TOTAL}} = {{PERCENT}}%.

---

## Violation Log

<!--
[REQUIRED] This table must appear in every report, even when no violations were recorded.
When no violations exist: include the header row, then write "_No violations recorded._" below.

ID format: V-### (three digits, zero-padded). IDs must be sequential starting from V-001.
Severity values: critical | major | minor  (lowercase, no variations)

Column guidance:
  Rule     — the specific rule or constraint that was violated (cite the agent file / AGENTS.md section if applicable)
  Expected — what the agent should have done
  Actual   — what the agent actually did (factual, observable)
  Evidence — the specific observable artifact: chat log turn, file path, tool call, or quoted excerpt

Example row:
  | V-001 | TC-021 | Delegation | ARTHUR must not create agents himself | ARTHUR delegates agent creation to MERLIN | ARTHUR attempted to create agent file directly | major | TC-021 response — ARTHUR file creation action observed. |
-->

| ID | TC | Category | Rule | Expected | Actual | Severity | Evidence |
|---|---|---|---|---|---|---|---|
{{VIOLATION_ROWS}}

---

## Top Violation Patterns

<!--
[REQUIRED] Always present. When no violations exist, write: "No violations observed in this run."
List patterns ordered by severity-weighted frequency (critical first, then major, then minor).
Use a numbered list. Maximum 5 patterns.

Each entry format:
  N. **Pattern name (Category)** — explanation of the pattern, which TC(s) it appeared in,
     and any relevant comparison to prior runs if this is a regression report.

When fewer than 3 violations, group them individually or note "No repeating patterns."
-->

{{TOP_VIOLATION_PATTERNS}}

---

## Reproduction

<!--
[REQUIRED] All fields are required. Fill in from run metadata.
"Baseline compared against" is REQUIRED for regression runs; OMIT for baseline runs.
"Post-test additions": if none, write "None."
-->

- **Test corpus**: `{{TEST_CORPUS_PATH}}`
- **Test cases run**: {{TC_LIST}}
- **Rubric**: `{{RUBRIC_PATH}}` v{{RUBRIC_VERSION}}
- **Model**: `{{MODEL_ID}}` via Copilot; verified by {{VERIFICATION_DESCRIPTION}}
- **Dispatch method**: {{DISPATCH_DESCRIPTION}}
<!-- Pre-test and Post-test snapshots are required fields. LENS uses these to verify
     artifact placement compliance (FR-033). List all relevant directories:
     artifacts/, .github/agents/, .github/agents/temps/, team-roster.md. -->
- **Pre-test snapshot**: `artifacts/` = {{ARTIFACTS_STATE}}; `.github/agents/` = {{AGENTS_STATE}}
- **Post-test additions (before cleanup)**: {{POST_TEST_ADDITIONS}}

<!--
[REQUIRED for regression runs only — omit for baseline runs]
- **Baseline compared against**: `{{BASELINE_RUN_ID}}`
-->

---

## Notes and Caveats

<!--
[OPTIONAL SECTION] Include when any of the following apply; omit the entire section otherwise.
Do not leave a blank section header.

Include notes for:
  - Test contamination: files modified or created by earlier test cases that affected later ones
  - Cleanup actions: what was removed and when; anything deferred to the user
  - Coverage gaps beyond the standard caveat in Overall (e.g., a specific category with 1 test)
  - Low-n confidence: categories where n < 3 tests should be treated as "no regression observed"
    rather than "category is healthy"
  - Rubric consistency: any deviation from the standard rubric or category assignments
  - Reproducibility threats: pre-existing state that made a test scenario non-pristine
-->

{{NOTES_AND_CAVEATS}}

---

<!--
═══════════════════════════════════════════════
OPTIONAL SECTION — Baseline / Prior Comparison
═══════════════════════════════════════════════
Include this section for regression runs that compare directly against a prior baseline,
or for runs that are part of a multi-model comparison series.
Remove this comment block and the placeholder below if the section is not needed.

For a regression run, use the heading:
  ## Baseline Comparison (vs. {{BASELINE_RUN_ID}})

For a multi-model series, use the heading:
  ## Comparison vs. Prior Baselines

Include:
  1. A comparison table (metrics as rows, runs as columns)
  2. "What improved" — numbered list of tests that moved from FAIL to PASS or severity decreased
  3. "What regressed" — numbered list of tests that moved from PASS to FAIL or severity increased
  4. Pattern shifts — notable behavioral changes vs. the baseline(s)

{{COMPARISON_SECTION}}
-->
