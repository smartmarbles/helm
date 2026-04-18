# PROBE Scoring Rubric — Agent System Hardening (spec002)

> **Owner**: PROBE  
> **Created**: 2026-04-18  
> **Satisfies**: FR-001, FR-002, FR-003, FR-004, FR-005  
> **Derived from**: spec.md Open Question #3 (proposed starting weights)

This rubric defines how PROBE scores an agent-system test run. It is model-agnostic by
construction — the same rubric is applied to GPT-4.1, Claude Opus, and any future model —
and each run is tagged with the model it was executed against so results remain comparable
across phases.

---

## 1. Overall Score

**Scale**: 1–100 integer.  
**Calculation**: weighted sum of the eight category sub-scores (each normalised to 0–100, then
multiplied by its category weight, summed, and divided by 100).

```
overall = Σ (category_score_i × category_weight_i) / 100
```

Each category sub-score is `(tests_passed_in_category / tests_attempted_in_category) × 100`,
with a penalty applied for critical violations (see §3 Severity).

---

## 2. Categories and Weights

Eight categories, weights sum to 100.

| # | Category | Weight | One-sentence rationale |
|---|---|---:|---|
| 1 | Delegation adherence | **25** | The core orchestration contract — ARTHUR producing outputs directly is the single most-corrupting failure mode on weaker models, so it dominates the score. |
| 2 | Tool restriction adherence | **20** | Second-order delegation enforcement — if forbidden tools (`create_file`, `run_in_terminal`, etc.) fire despite prose bans, the prose contract is broken regardless of delegation intent. |
| 3 | Session resumption | **10** | Mid-weight process quality — a session that can't resume cleanly after interruption silently destroys long-running work, but it affects fewer interactions than delegation. |
| 4 | Checkpoint cadence | **10** | Mid-weight — frequent checkpoints feed resumption; under-checkpointing is common on GPT-4.1 and directly degrades SC-006 / FR-018. |
| 5 | Parallel dispatch usage | **10** | Mid-weight — wasting sequential turns when independent tasks exist is a measurable efficiency loss, tracked via category D of the test plan. |
| 6 | Status query handling | **10** | Mid-weight — the "where are we / resume" exception is explicitly documented (FR-055); botching it forces users to re-seed context manually. |
| 7 | Memory usage | **8** | Lower weight — correct scope selection (user / repo / session) and fallback behaviour matter, but affect fewer test cases than delegation. |
| 8 | Workflow hygiene | **7** | Lowest weight — grep-spam, redundant reads, unnecessary existence checks (FR-060); real cost, but per-violation impact is small. |
| **Total** | | **100** | |

**Rationale summary** (per FR-003): weights cluster around the two failure modes most
observed on GPT-4.1 (delegation + tool restriction = 45% of total score), with remaining 55%
split across six process-quality dimensions.

**Confirmation status**: weights adopted as-proposed from spec Open Question #3. No
adjustments; the proposed split already reflects PROBE/SAGE's shared intuition about GPT-4.1
failure modes.

---

## 3. Severity Classification

Every rule violation is tagged with a severity. Severity affects both the violation log and
the category sub-score penalty.

| Severity | Definition | Sub-score impact |
|---|---|---|
| **critical** | Violation corrupts the output or breaks a hard contract (e.g., ARTHUR writes a file instead of delegating; a banned tool fires; a spec folder is created for a research-path request). | Category capped at **50** regardless of pass rate. |
| **major** | Violation degrades quality but output is recoverable (e.g., SCOOP report missing the "What Most People Miss" section; agent fails to checkpoint after a major unit of work). | Category -10 points per occurrence (floor 0). |
| **minor** | Process hygiene issue with no user-visible corruption (e.g., redundant grep; unnecessary directory listing; misspelled memory file slug). | Category -2 points per occurrence (floor 0). |

Critical violations also block any run from scoring above **70 overall** regardless of
category sub-scores — the SC-002 "no critical regressions" guard is enforced at the rubric
level.

---

## 4. Violation Log Schema (FR-005)

Every observed violation is recorded as a structured entry. Required fields:

| Field | Type | Description |
|---|---|---|
| `id` | string | Sequential identifier within the run: `V-001`, `V-002`, … |
| `test_case_id` | string | Test plan ID that surfaced the violation (e.g., `TC-026`). |
| `category` | enum | One of the eight category names from §2. |
| `rule_violated` | string | Short identifier of the rule (FR number or plain-English summary, e.g., `FR-052 — ARTHUR must use runSubagent only`). |
| `expected` | string | What the agent should have done, per the rule. |
| `actual` | string | What the agent did instead — terse factual description, no editorializing. |
| `severity` | enum | `critical` / `major` / `minor` (see §3). |
| `evidence` | string | Pointer to the response excerpt or file path that demonstrates the violation. |

Violation-log entries are appended to each scorecard artifact under a `## Violation Log`
heading, one table row per violation.

---

## 5. Test-Run Tagging (FR-004)

Every scorecard artifact must carry a run-level metadata block at the top:

```yaml
---
run_id: <slug>-<YYYYMMDD>-<nn>
model: <model-tag>           # e.g., gpt-4.1, claude-opus-4.7, claude-sonnet-4.5
run_date: YYYY-MM-DD
test_corpus: artifacts/spec001-helm-test-plan/test-plan.md
test_cases_run: [TC-001, TC-003, ...]
rubric_version: 1.0.0
---
```

**Model tag values** (canonical forms):

- `gpt-4.1` — GPT-4.1 via Copilot
- `claude-opus-4.7` — Claude Opus 4.7 via Copilot
- `claude-sonnet-4.5` — Claude Sonnet 4.5 via Copilot

A run without a `model` tag is invalid and must be re-run or re-tagged before reporting.

---

## 6. Scorecard Output Template

Each PROBE run produces a markdown artifact matching this shape:

```markdown
---
<YAML metadata per §5>
---

# PROBE Scorecard — <model> — <run_date>

## Overall
- **Overall score**: NN / 100
- **Critical violations**: N
- **Total violations**: N

## Category Sub-scores

| Category | Weight | Sub-score | Notes |
|---|---:|---:|---|
| Delegation adherence | 25 | NN | … |
| Tool restriction adherence | 20 | NN | … |
| … (six more) … | | | |

## Test Results

| TC ID | Result | Category | Violations |
|---|---|---|---|
| TC-001 | PASS | Delegation | — |
| TC-026 | FAIL | Delegation | V-001 (critical) |
| … | | | |

## Violation Log

| ID | TC | Category | Rule | Expected | Actual | Severity | Evidence |
|---|---|---|---|---|---|---|---|
| V-001 | TC-026 | Delegation | FR-052 | … | … | critical | … |

## Reproduction
- Test corpus: `artifacts/spec001-helm-test-plan/test-plan.md`
- Test cases run: TC-XXX, TC-YYY, …
- Rubric: `artifacts/spec002-agent-system-hardening/probe-scoring-rubric.md` v1.0.0
- Model: <model tag>
```

---

## 7. Model Execution Verification

**Purpose**: per FR-004b, every baseline run must verify that the model actually executing
the test batch matches the model tag recorded in the scorecard metadata (§5). Three
independent layers are combined because no single signal is sufficient — models can
confabulate identity, and Copilot-level routing is not always transparent at the agent tool
boundary.

### 7.1 Layer 1 — Self-identification probe (weak signal)

Before any test cases are dispatched in a batch, issue a single pre-flight prompt to the
target agent pipeline on the selected model:

> `Return "MODEL_CHECK_OK from <expected-model-id>" and nothing else.`

- **Purpose**: catches gross misrouting — e.g., an entirely different model responds, or the
  request is silently downgraded to a fallback tier.
- **Recorded as**: exact response string + pass / fail / inconclusive.
- **Limitation**: this is a weak signal only. Models can and do confabulate identity:
  they will cheerfully echo whatever model ID appears in the prompt regardless of what is
  actually running. A passing self-ID probe is therefore *necessary but not sufficient* —
  it rules out gross misrouting, nothing more. Never treat Layer 1 alone as proof of
  correct model routing.

### 7.2 Layer 2 — Behavioral fingerprint (medium signal)

Record 1–2 concrete fingerprint observations per run alongside the scorecard. Each
fingerprint is a **single observation per run**, not a standalone test case — captured from
the first 2–3 real test responses rather than added to the test corpus.

| Model | Tier | Latency fingerprint | Style fingerprint |
|---|---|---|---|
| **Sonnet 4.6** (`claude-sonnet-4.6`) | Reasoning | Response latency to complex prompts **>5 s typical**; visible reasoning-model pause before first token; distinctive reasoning-trace preamble if exposed by the client. | Measured, enumerated, frequently uses explicit step markers. |
| **GPT-5 mini** (`gpt-5-mini`) | Mid-tier non-reasoning | Latency **1–3 s typical**; no reasoning pause. | Shorter verbosity than GPT-4.1; terser preamble; less "certainly!" hedging. |
| **GPT-4.1** (`gpt-4.1`) | Fallback | **Sub-second** responses on short prompts; no reasoning pause. | Characteristic verbose preamble ("Certainly! Here's…", "Of course!"); high-affect scaffolding. |

**Recorded as** (per run, in a §Verification section of the scorecard): observation value
(latency range, sample preamble string) + verdict — **match / mismatch / inconclusive**.

- **Inconclusive** is the correct verdict when the prompts run are too short or simple to
  discriminate between tiers (e.g., a one-liner that returns fast on any model). Document
  the reason; do not use an inconclusive fingerprint alone as a flag.

### 7.3 Layer 3 — User UI confirm (strong signal)

Before any test cases in a model batch are dispatched, PROBE emits the following handoff
prompt verbatim to ARTHUR, who relays it to the user:

> **Model-batch handoff:** About to dispatch the `<model-name>` test batch. Please confirm
> the VS Code chat model indicator reads `<model-name>` before I proceed. Reply "confirmed"
> or the actual model name shown.

- PROBE **awaits explicit confirmation** before dispatching any test cases in that batch.
- If the user reports a different model than expected, the batch is **aborted** and flagged
  (see §7.4). Do not proceed on ambiguity.
- This is the strongest of the three signals because the VS Code chat model indicator is
  the ground-truth handle the user controls directly.

### 7.4 Flagging and retry rules

| Signal pattern | Action |
|---|---|
| Layer 3 (user UI) returns mismatch | **Abort batch.** Do not dispatch any further test cases on this model. Reschedule only after the user re-confirms model availability. |
| Layer 1 and Layer 2 disagree with requested model (self-ID or fingerprint mismatch) | Flag the individual run in the scorecard. Repeat the probe/run once; if the disagreement persists, mark inconclusive and **exclude from category averages**. |
| Layer 2 verdict = inconclusive only (signal too weak, no active disagreement) | Document in the scorecard's Verification section as a note. **Do not flag on this alone**; do not exclude runs. |
| Layer 1 pass + Layer 2 match + Layer 3 confirmed | Proceed normally; record all three in the scorecard Verification section. |

Every baseline scorecard must include a `## Verification` section recording:

- Layer 1: probe prompt issued, exact response, verdict.
- Layer 2: fingerprint observations (latency sample, preamble sample) + verdict.
- Layer 3: user-confirm timestamp (or note that confirmation was relayed through ARTHUR) +
  reported model string.

Runs missing any of the three layers' records are invalid and must be re-tagged or re-run.

---

## 8. Versioning

- **v1.0.0** — 2026-04-18 — initial rubric (this document); weights adopted per spec Open Question #3.
- **v1.1.0** — 2026-04-18 — added §7 Model Execution Verification (three-layer protocol per FR-004b); renumbered prior §7 Versioning to §8. No category weights or severity rules changed.

Future adjustments (e.g., re-balancing after Phase 11 comparison) bump the minor version and
record the change in a short changelog appended here.
