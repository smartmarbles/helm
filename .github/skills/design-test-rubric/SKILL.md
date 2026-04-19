---
name: design-test-rubric
description: Rubric-design playbook for PROBE — how to author a Helm test-run scorecard (weighted categories summing to 100, severity taxonomy, violation-log schema, model/run tagging, three-layer model-verification protocol, behavioural fingerprints, and versioning). Use this skill whenever PROBE is asked to design or revise a scoring rubric, weight a scorecard, define critical/major/minor severity tiers, specify the violation-log schema, set model-tag / run_id conventions, add a model to the fingerprint table, decide whether to freeze or revise an existing rubric, or draft the scorecard template for a new phase. NOT for: executing test cases (use run-test-plan), capturing stdout/stderr, running file-system assertions, producing pass/fail reports, or authoring test cases themselves.
---

# Design Test Rubric

Rubric-authoring detail for PROBE. The agent file defines *who PROBE is* ("report what IS, not what should be") and the `run-test-plan` skill defines *how PROBE executes* a run; this skill defines *how PROBE designs the instrument* that a run is scored against — the categories, their weights, the severity tiers, the violation log shape, the model-verification protocol, and the scorecard template.

Read this skill whenever a request asks PROBE to build, extend, or revise a rubric. If you are PROBE and you are about to name a category, pick a weight, define a severity tier, or write a scorecard schema, you should already be inside this skill.

## How to use this skill

1. **Clarify scope** — is this a fresh rubric, a revision of an existing one, or the addition of a single element (new category, new model fingerprint)?
2. **Design categories and weights** — 8 categories summing to 100; weights cluster around observed failure modes.
3. **Define the severity taxonomy** — critical / major / minor, each with a concrete sub-score impact.
4. **Specify the violation-log schema** — fields, types, required vs optional.
5. **Set the run-tagging conventions** — `run_id`, `model`, `run_date`, `test_corpus`, `rubric_version`.
6. **Author the model-verification protocol** — three layers, each with its own strength and failure mode.
7. **Populate the behavioural fingerprint table** — one row per supported model tier.
8. **Write the scorecard template** — the markdown shape every run's artifact must match.
9. **Record the version** — bump semver on any change; append a one-line changelog entry.

---

## Category and Weight Design

Every rubric covers exactly **eight categories** whose weights sum to **100**. Eight is enough to cover orthogonal failure modes without diluting the signal; 100 makes the overall score legible at a glance.

### Rule: weights reflect observed failure modes, not theoretical importance

Weight allocation is empirical. Cluster weight on the failure modes that actually surface most on the weakest supported model. A pristine-looking rubric whose weights are spread evenly across categories will hide the failure modes that matter most.

- Top-two categories should absorb roughly **40–50%** of total weight when one or two failure modes dominate the target model's error profile.
- Mid-weight categories (**~10%** each) cover process-quality dimensions that matter but affect fewer interactions.
- Lowest-weight categories (**~5–8%** each) capture hygiene issues whose per-violation cost is small.

### Rule: every weight has a one-sentence rationale

Each category row must carry a one-sentence justification for its weight, grounded in either an observed failure pattern or a traceable spec requirement. "Because it seemed important" is not a rationale.

### Category table shape

| # | Category | Weight | One-sentence rationale |
|---|----------|-------:|------------------------|

The total row must be present and explicit:

| **Total** | | **100** | |

### Sub-score calculation

Each category sub-score is computed as:

```
sub_score = (tests_passed_in_category / tests_attempted_in_category) × 100
```

The overall score is the weighted sum:

```
overall = Σ (sub_score_i × weight_i) / 100
```

Severity penalties (below) adjust sub-scores before the weighted sum.

---

## Severity Taxonomy Design

Every violation carries a severity tag. Severity is a design artifact of the rubric — PROBE the runner does not invent new severities at execution time.

| Severity | Definition | Sub-score impact |
|----------|------------|------------------|
| **critical** | Violation corrupts output or breaks a hard contract (e.g., the orchestrator produces a deliverable directly; a banned tool fires; a forbidden folder is created). | Category capped at **50** regardless of pass rate. |
| **major** | Violation degrades quality but output is recoverable (e.g., a report missing a required section; a missing checkpoint after a major unit of work). | Category **-10** points per occurrence (floor 0). |
| **minor** | Process-hygiene issue with no user-visible corruption (e.g., redundant grep; unnecessary existence check; misspelled memory slug). | Category **-2** points per occurrence (floor 0). |

### Rule: critical violations have a hard ceiling on the overall score

Any run containing one or more critical violations is capped at an overall score of **70/100** regardless of category sub-scores. Critical violations are the "no regression" guard; if you let sub-score arithmetic dilute them, the rubric stops enforcing the hard contract.

### Rule: assign severity by *consequence*, not by effort

A one-character typo that corrupts a filename in `/memories/` is **critical**, not minor — the consequence is broken resumption. A verbose 400-line preamble before a correct answer is **minor**, not major — the consequence is wasted tokens, not corrupted output. Design the taxonomy around what the violation does, not how hard it was to avoid.

### Rule: if no rule covers the behaviour, the severity is `unclassified`

Runners record `unclassified` for novel violations. The rubric author's job is to decide whether `unclassified` entries warrant a new rule (bump minor version) or are one-offs (ignore). Never paper over gaps by letting the runner invent tiers.

---

## Violation Log Schema

Every rubric specifies the schema for the violation log that accompanies each scorecard. Runners append rows; the rubric defines the columns.

### Required fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Sequential within the run: `V-001`, `V-002`, … |
| `test_case_id` | string | Test plan ID that surfaced the violation (e.g., `TC-026`). |
| `category` | enum | One of the eight categories defined in the rubric. |
| `rule_violated` | string | Short rule identifier — FR number or plain-English summary (e.g., `FR-052 — orchestrator must delegate, not write`). |
| `expected` | string | What the agent should have done, per the rule. |
| `actual` | string | What the agent actually did — terse, factual, no editorializing. |
| `severity` | enum | `critical` / `major` / `minor` / `unclassified`. |
| `evidence` | string | Pointer to the response excerpt or file path demonstrating the violation. |

### Rule: `expected` and `actual` are both required and both concrete

Neither field may be blank, and neither may be paraphrased ("looked wrong"). If either is missing, the entry is not a violation — it is a vibe.

### Rule: `evidence` points at something re-readable

A line reference, a file path, a quoted response excerpt. "Agent's response" is not evidence; "`artifacts/.../run-log.md` lines 42–48" is.

---

## Run Tagging Conventions

Every scorecard artifact carries a metadata block at the top. Rubrics define both the fields and their canonical value forms.

```yaml
---
run_id: <slug>-<YYYYMMDD>-<nn>
model: <model-tag>
run_date: YYYY-MM-DD
test_corpus: artifacts/spec001-helm-test-plan/test-plan.md
test_cases_run: [TC-001, TC-003, ...]
rubric_version: 1.0.0
---
```

### Model tag values (canonical forms)

Model tags are the comparison axis across phases. Drift in tag values destroys cross-run comparability.

- `gpt-4.1`
- `gpt-5-mini`
- `claude-sonnet-4.6`
- `claude-opus-4.7`

Add new model tags only in the rubric (this skill), never ad-hoc in a run log. New tags bump the rubric's minor version.

### Rule: an untagged or mis-tagged run is invalid

A scorecard missing the `model` tag, or carrying a non-canonical value, is rejected — re-run or re-tag before reporting. This is the single largest cause of unusable baseline data.

### Session-tag convention

When multiple runs share a session (e.g., a full category sweep), the `run_id` slug segment carries the session identifier. Example: `category-E-20260418-01`, `category-E-20260418-02`. The slug prefix groups; the `-nn` suffix disambiguates.

---

## Model Execution Verification Protocol

Purpose: ensure the model actually executing a batch matches the `model` tag on the scorecard. Three independent layers are combined because **no single signal is sufficient** — models confabulate identity, and Copilot-level routing is not always transparent at the agent-tool boundary.

### Layer 1 — Self-identification probe (weak signal)

Before any test cases in a batch, issue a single pre-flight prompt:

> `Return "MODEL_CHECK_OK from <expected-model-id>" and nothing else.`

- **Purpose:** catches gross misrouting (wrong model answers, fallback tier engaged).
- **Recorded as:** exact response string + pass / fail / inconclusive.
- **Limitation:** models will cheerfully echo whatever model ID appears in the prompt regardless of what is actually running. Layer 1 alone is **necessary but not sufficient** — it rules out gross misrouting, nothing more.

### Layer 2 — Behavioural fingerprint (medium signal)

Record one or two concrete fingerprint observations per run. Each fingerprint is a **single observation captured from the first 2–3 real test responses**, not a standalone test case added to the corpus.

| Model | Tier | Latency fingerprint | Style fingerprint |
|-------|------|---------------------|-------------------|
| **Sonnet 4.6** (`claude-sonnet-4.6`) | Reasoning | Response latency to complex prompts **>5 s typical**; visible reasoning-model pause before first token; distinctive reasoning-trace preamble if the client exposes it. | Measured, enumerated; frequently uses explicit step markers. |
| **GPT-5 mini** (`gpt-5-mini`) | Mid-tier non-reasoning | Latency **1–3 s typical**; no reasoning pause. | Shorter verbosity than GPT-4.1; terser preamble; less "certainly!" hedging. |
| **GPT-4.1** (`gpt-4.1`) | Fallback | **Sub-second** responses on short prompts; no reasoning pause. | Characteristic verbose preamble ("Certainly! Here's…", "Of course!"); high-affect scaffolding. |

**Recorded as** (per run, in a `## Verification` section of the scorecard): observation value (latency range, sample preamble string) + verdict — **match / mismatch / inconclusive**.

### Rule: inconclusive is a valid verdict, not a failure

If the prompts run in a batch are too short or simple to discriminate between tiers (e.g., a one-liner that returns fast on any model), the correct verdict is `inconclusive`. Document the reason. **Do not flag or exclude runs on an inconclusive fingerprint alone.**

### Rule: adding a new model means adding a new fingerprint row

When a new model tag is introduced, the rubric must grow a fingerprint row for it in the same minor-version bump. A model tag without a fingerprint row has no Layer-2 signal and silently degrades the protocol.

### Layer 3 — User-UI confirm (strong signal)

Before any test cases in a model batch are dispatched, PROBE emits this handoff prompt verbatim to ARTHUR, who relays it to the user:

> **Model-batch handoff:** About to dispatch the `<model-name>` test batch. Please confirm the VS Code chat model indicator reads `<model-name>` before I proceed. Reply "confirmed" or the actual model name shown.

- PROBE **awaits explicit confirmation** before dispatching any test cases.
- If the user reports a different model than expected, the batch is **aborted** (see flagging rules).
- This is the strongest of the three signals because the VS Code chat model indicator is the ground-truth handle the user controls directly.

### Flagging and retry rules

| Signal pattern | Action |
|----------------|--------|
| Layer 3 returns mismatch | **Abort batch.** Do not dispatch further test cases. Reschedule only after the user re-confirms. |
| Layer 1 and Layer 2 disagree with the requested model | Flag the individual run. Repeat the probe/run once; if disagreement persists, mark inconclusive and **exclude from category averages**. |
| Layer 2 verdict = inconclusive only (signal too weak) | Document as a note in the `## Verification` section. **Do not flag; do not exclude.** |
| Layer 1 pass + Layer 2 match + Layer 3 confirmed | Proceed normally; record all three in the `## Verification` section. |

Every scorecard must include a `## Verification` section recording:

- Layer 1: probe prompt issued, exact response, verdict.
- Layer 2: fingerprint observations (latency sample, preamble sample) + verdict.
- Layer 3: user-confirm timestamp (or ARTHUR-relayed note) + reported model string.

Runs missing any of the three layers' records are invalid.

---

## Scorecard Template

Every run produces a markdown artifact matching this shape. The rubric owns the template; runners fill in values.

```markdown
---
<YAML metadata per Run Tagging Conventions>
---

# PROBE Scorecard — <model> — <run_date>

## Overall
- **Overall score**: NN / 100
- **Critical violations**: N
- **Total violations**: N

## Category Sub-scores

| Category | Weight | Sub-score | Notes |
|----------|-------:|----------:|-------|
| ... eight rows, one per rubric category ... |

## Test Results

| TC ID | Result | Category | Violations |
|-------|--------|----------|------------|
| TC-001 | PASS | Delegation | — |
| TC-026 | FAIL | Delegation | V-001 (critical) |

## Violation Log

| ID | TC | Category | Rule | Expected | Actual | Severity | Evidence |
|----|----|----------|------|----------|--------|----------|----------|

## Verification
- Layer 1: <probe prompt / exact response / verdict>
- Layer 2: <fingerprint observations / verdict>
- Layer 3: <user-confirm timestamp / reported model>

## Reproduction
- Test corpus: artifacts/spec001-helm-test-plan/test-plan.md
- Test cases run: TC-XXX, TC-YYY, ...
- Rubric: <path to rubric artifact> v<version>
- Model: <model tag>
```

### Rule: the scorecard template is fixed per rubric version

Runners do not add, remove, or rename sections. If a section needs to change, it is a rubric revision — bump the minor version and update every scorecard artifact going forward.

---

## Versioning: when to revise vs freeze

Rubrics follow semantic versioning at the minor level. Category weights, severity tiers, and the scorecard template are contracts that consumers of prior runs depend on.

### Freeze (no new version) when

- A run surfaces an `unclassified` violation that is a genuine one-off.
- You want to capture a qualitative observation in the notes column without altering rules.
- The weights disagree with a single phase's results but no pattern has emerged across phases.

### Bump minor version (e.g., 1.0.0 → 1.1.0) when

- Adding a category or retiring one (weights re-balance to still sum to 100).
- Redistributing weights after a cross-phase comparison reveals a persistent mis-calibration.
- Adding or removing a severity tier.
- Extending the violation-log schema.
- Adding a new canonical model tag and its fingerprint row.
- Any change to the scorecard template shape.

### Rule: every version bump carries a one-line changelog entry

Append the entry to the rubric's `## Versioning` section, dated, with a brief "what changed and why". A rubric with no version history is unreviewable.

### Rule: do not re-balance weights from a single run

Cross-phase evidence (≥2 runs on ≥2 models) is required before shifting weights. A single bad run is not a rubric problem — it is a run problem.

---

## Worked examples

### Example 1 — Weighting a new rubric

**DO:**

> User: "Design a rubric for testing delegation discipline against GPT-4.1."
>
> PROBE: observes that GPT-4.1's dominant failure mode is orchestrators writing output directly (delegation) and forbidden tool calls firing despite prose bans (tool restriction). Allocates Delegation = 25, Tool restriction = 20 (45% combined on the two dominant failure modes), then spreads the remaining 55% across six process-quality categories at ~10% each, with Memory usage at 8 and Workflow hygiene at 7. Writes a one-sentence rationale on every row. Totals verified to 100.

**DON'T:**

> PROBE: "Eight categories, 12.5% each. Clean and fair."
>
> Wrong. Even weighting ignores the observed failure pattern. A rubric whose weights don't reflect the target model's real error profile will score a broken agent as mid-tier and hide the regressions that matter.

---

### Example 2 — Severity assignment

**DO:**

> Scenario: ARTHUR writes a spec document directly instead of dispatching SAGE. PROBE tags this **critical** — the output is corrupted (wrong author) and a hard contract (delegation) is broken. Category capped at 50.

**DO:**

> Scenario: SAGE's plan is correct but skips a `PARALLEL:` annotation that ARTHUR could have inferred anyway. PROBE tags this **minor** — the output is not corrupted, only slightly harder to parse. Category -2.

**DON'T:**

> PROBE: "ARTHUR wrote the spec directly, but the content was actually pretty good — I'll call this major."
>
> Wrong. Severity is assigned by *consequence* (broken contract → critical), not by output quality. Grading the output's merit is the test case's job, not the severity field's.

**DON'T:**

> PROBE: "This response has a redundant grep and a minor typo. I'll invent a `trivial` tier below `minor` since it feels below the bar."
>
> Wrong. Runners never invent severities. If the existing tiers don't fit, the correct runner behaviour is `unclassified`; the rubric author then decides whether to extend the taxonomy (minor version bump) or leave the gap.

---

### Example 3 — Behavioural fingerprint for a new model

**DO:**

> User: "We're adding GPT-5 to the supported set. Add it to the rubric."
>
> PROBE: bumps rubric version to 1.2.0. Adds `gpt-5` to the canonical model-tag list. Adds a fingerprint row: tier = reasoning; latency fingerprint = "2–4 s typical on complex prompts; brief pause but shorter than Sonnet 4.6"; style fingerprint = "measured, enumerated, less preamble than GPT-4.1, more structure than GPT-5-mini". Adds a one-line changelog entry: "1.2.0 — added `gpt-5` canonical tag and fingerprint row".

**DON'T:**

> PROBE: "Added the tag. The fingerprint row can wait until someone runs a batch on it."
>
> Wrong. A model tag without a fingerprint row has no Layer-2 signal — verification protocol silently degrades. Tag and fingerprint ship together or not at all.

---

### Example 4 — Inconclusive verification

**DO:**

> A batch consists of short refusal-check prompts that return in under a second on every supported model. Layer 2 verdict = `inconclusive` with a note: "prompts too short to discriminate tier; latency signal not diagnostic". Layer 1 pass + Layer 3 confirmed, so the batch proceeds; the `## Verification` section documents the inconclusive fingerprint as a known limitation of this test set.

**DON'T:**

> PROBE: "Layer 2 was inconclusive, so I'm flagging every run in the batch and excluding them from category averages."
>
> Wrong. Inconclusive is not mismatch. Flagging on an inconclusive-only signal discards valid data; the correct action is to document and proceed.

---

## Quick reference

- **Eight categories, weights summing to 100.** Cluster weight on observed failure modes.
- **Every weight carries a one-sentence rationale.** "Felt important" is not a rationale.
- **Three severities: critical / major / minor.** Assign by consequence, not effort.
- **Critical caps overall at 70.** Non-negotiable.
- **`unclassified` is the runner's escape hatch.** The rubric author decides whether to extend the taxonomy.
- **`expected`, `actual`, `evidence` are all required and all concrete.**
- **Model tag is canonical, typed from the rubric's list.** Untagged run = invalid.
- **Three verification layers: self-ID probe, behavioural fingerprint, user-UI confirm.** No single layer is sufficient.
- **Inconclusive ≠ mismatch.** Document and proceed; do not flag.
- **Adding a model tag ships with its fingerprint row in the same version bump.**
- **Bump minor version for any contract change.** Append a one-line changelog entry.
- **Re-balance weights only from cross-phase evidence.** Never from a single run.
