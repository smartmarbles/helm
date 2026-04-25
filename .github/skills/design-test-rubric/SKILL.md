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

→ [Category Table Shape and Sub-score Formulas](references/category-weight-tables.md) — column scaffold, required total row, and weighted sub-score calculation formulas

---

## Severity Taxonomy Design

Every violation carries a severity tag. Severity is a design artifact of the rubric — PROBE the runner does not invent new severities at execution time.

→ [Severity Taxonomy Table](references/severity-taxonomy.md) — critical/major/minor definitions and sub-score impact

### Rule: critical violations have a hard ceiling on the overall score

Any run containing one or more critical violations is capped at an overall score of **70/100** regardless of category sub-scores. Critical violations are the "no regression" guard; if you let sub-score arithmetic dilute them, the rubric stops enforcing the hard contract.

### Rule: assign severity by *consequence*, not by effort

A one-character typo that corrupts a filename in `/memories/` is **critical**, not minor — the consequence is broken resumption. A verbose 400-line preamble before a correct answer is **minor**, not major — the consequence is wasted tokens, not corrupted output. Design the taxonomy around what the violation does, not how hard it was to avoid.

### Rule: if no rule covers the behaviour, the severity is `unclassified`

Runners record `unclassified` for novel violations. The rubric author's job is to decide whether `unclassified` entries warrant a new rule (bump minor version) or are one-offs (ignore). Never paper over gaps by letting the runner invent tiers.

---

## Violation Log Schema

Every rubric specifies the schema for the violation log that accompanies each scorecard. Runners append rows; the rubric defines the columns.

→ [Violation Log Required Fields](references/violation-log-schema.md) — field names, types, and descriptions

### Rule: `expected` and `actual` are both required and both concrete

Neither field may be blank, and neither may be paraphrased ("looked wrong"). If either is missing, the entry is not a violation — it is a vibe.

### Rule: `evidence` points at something re-readable

A line reference, a file path, a quoted response excerpt. "Agent's response" is not evidence; "`artifacts/.../run-log.md` lines 42–48" is.

---

## Run Tagging Conventions

→ [Run Tagging Reference](references/run-tagging-conventions.md) — canonical YAML block shape and model tag values

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

→ [Model Behavioural Fingerprints](references/model-fingerprints.md) — per-model latency and style fingerprints for Layer 2 verification

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

→ [Flagging and Retry Rules](references/model-fingerprints.md#flagging-and-retry-rules) — signal-pattern → action lookup for non-nominal layer signals

Every scorecard must include a `## Verification` section recording:

- Layer 1: probe prompt issued, exact response, verdict.
- Layer 2: fingerprint observations (latency sample, preamble sample) + verdict.
- Layer 3: user-confirm timestamp (or ARTHUR-relayed note) + reported model string.

Runs missing any of the three layers' records are invalid.

---

## Scorecard Template

→ [Scorecard Template](references/scorecard-template.md) — full markdown scaffold and fixed-per-version rule

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

→ [Worked Examples](references/worked-examples.md) — four DO/DON'T scenario pairs (weighting, severity, new-model fingerprint, inconclusive verification)

---

## Quick reference

→ [Quick Reference](references/quick-reference.md) — condensed cheat-sheet of all key rules
