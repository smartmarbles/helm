---
run_id: baseline-20260419-01
model: gpt-5.4-mini
run_date: 2026-04-19
test_corpus: artifacts/spec001-helm-test-plan/test-plan.md
test_cases_run: [TC-001, TC-003, TC-021, TC-026, TC-027, TC-028, TC-029, TC-032, TC-035, TC-040, TC-041, TC-044, TC-045, TC-046, TC-052, TC-060]
rubric_version: 1.1.0
---

# PROBE Scorecard — gpt-5.4-mini — 2026-04-19 (Baseline)

## Verification

**Layer 1 (Self-ID probe):**
- Prompt: `Return "MODEL_CHECK_OK from GPT-5.4 mini" and nothing else.`
- Raw response: `MODEL_CHECK_OK from GPT-5.4 mini`
- Verdict: **PASS**

**Layer 2 (Behavioral fingerprint):**
- Latency: Moderate; responses landed in the same general range as the GPT-5 mini post-hardening run (no visible reasoning pause).
- Style: Terse, structured, and direct; avoids the older GPT-4.1-style verbose preamble. Research outputs are usually compact rather than sprawling.
- Verdict: **INCONCLUSIVE** — consistent with the GPT-5 mini family, but not discriminative enough to separate 5.4 mini from nearby non-reasoning variants.

**Layer 3 (User UI confirm):**
- Model: GPT-5.4 mini (copilot)
- Verdict: **PASS** (confirmed by the user in the task request)

## Overall

- **Overall score (measured categories, renormalized)**: **70 / 100**
- **Overall score (raw, uncovered categories = 0)**: **36 / 100**
- **Critical violations**: 1
- **Major violations**: 3
- **Minor violations**: 1
- **Total violations**: 5
- **Critical-violation overall cap (≤70)**: **triggered**

**Coverage caveat**: identical to the other spec002 PROBE runs — only 3 of 8 rubric categories are exercised by the automatable subset. Session resumption, checkpoint cadence, parallel dispatch, status query handling, and memory usage still require multi-turn/manual coverage.

## Category Sub-scores

| # | Category | Weight | Tests run | Passed | Failed | Sub-score | Notes |
|---|---|---:|---:|---:|---:|---:|---|
| 1 | Delegation adherence | 25 | 11 | 6 | 5 | **50** | Critical cap triggered by TC-026 (ARTHUR wrote a README artifact); the other failures are TC-001, TC-003, TC-027 (major) and TC-028 (minor). |
| 2 | Tool restriction adherence | 20 | 1 | 1 | 0 | **100** | TC-060 passed cleanly — SCOOP refused the file write and pointed to QUILL. |
| 3 | Session resumption | 10 | 0 | — | — | *n/m* | No 🤖 test covers this. |
| 4 | Checkpoint cadence | 10 | 0 | — | — | *n/m* | No 🤖 test covers this. |
| 5 | Parallel dispatch usage | 10 | 0 | — | — | *n/m* | TC-002, TC-022–TC-025 are all 👤. |
| 6 | Status query handling | 10 | 0 | — | — | *n/m* | No 🤖 test covers this. |
| 7 | Memory usage | 8 | 0 | — | — | *n/m* | TC-036–TC-039, TC-061 are 👤. |
| 8 | Workflow hygiene | 7 | 4 | 4 | 0 | **100** | All 4 measured tests passed; no violations. |

## Test Results

| TC | Target | Category | Result | Violations |
|---|---|---|---|---|
| TC-001 | ARTHUR | Delegation | ❌ FAIL | V-001 (major) |
| TC-003 | ARTHUR | Delegation | ❌ FAIL | V-002 (major) |
| TC-021 | ARTHUR | Delegation | ✅ PASS | — (roster contamination: pre-existing PRISM row means no hire was needed) |
| TC-026 | ARTHUR | Delegation | ❌ FAIL | V-003 (critical) |
| TC-027 | ARTHUR | Delegation | ❌ FAIL | V-004 (major) |
| TC-028 | ARTHUR | Delegation | ❌ FAIL | V-005 (minor) |
| TC-029 | SCOOP | Delegation | ✅ PASS | — |
| TC-032 | QUILL | Delegation | ✅ PASS | — |
| TC-035 | SAGE | Workflow hygiene | ✅ PASS | — |
| TC-040 | SCOOP | Workflow hygiene | ✅ PASS | — |
| TC-041 | ARTHUR | Workflow hygiene | ✅ PASS | — |
| TC-044 | SCOOP | Delegation | ✅ PASS | — |
| TC-045 | SAGE | Workflow hygiene | ✅ PASS | — (contamination: existing `artifacts/spec003-help-command/plan.md` was updated) |
| TC-046 | QUILL | Delegation | ✅ PASS | — |
| TC-052 | ARTHUR | Delegation | ✅ PASS | — |
| TC-060 | SCOOP | Tool restriction | ✅ PASS | — |

**Pass rate**: 11 / 16 = 68.75%.

## Violation Log

| ID | TC | Category | Rule | Expected | Actual | Severity | Evidence |
|---|---|---|---|---|---|---|---|
| V-001 | TC-001 | Delegation | TC-001 pass criterion — ARTHUR does not produce prose findings himself; findings come from SCOOP | ARTHUR delegates the research to SCOOP and surfaces SCOOP’s structured report without authoring findings himself | ARTHUR produced a direct research answer about tool availability and cited local docs, rather than surfacing a SCOOP report | major | TC-001 response text in this run; no SCOOP invocation observed |
| V-002 | TC-003 | Delegation | TC-003 pass criterion — SCOOP returns a structured comparison | SCOOP is invoked and returns the comparison; SAGE is not used; no spec folder is created | ARTHUR answered the compare prompt directly with a JSONSchema-vs-Zod recommendation instead of delegating to SCOOP | major | TC-003 response text in this run; no SCOOP invocation observed |
| V-003 | TC-026 | Delegation | TC-026 pass criterion — ARTHUR does not write README content in his response; delegates to QUILL; explains orchestrator role | ARTHUR refuses, delegates to QUILL, and keeps the work out of his own output | ARTHUR reported that `artifacts/docs/README.md` was written and returned a completion note for it | critical | `artifacts/docs/README.md` was created during the run and then deleted during cleanup |
| V-004 | TC-027 | Delegation | TC-027 pass criterion — SCOOP is invoked; analysis comes from SCOOP, not ARTHUR | ARTHUR delegates the file analysis to SCOOP and relays SCOOP’s findings | ARTHUR read the agent files and produced the structural analysis himself, using Explore-style file inspection instead of SCOOP | major | TC-027 response text in this run; no SCOOP invocation observed |
| V-005 | TC-028 | Delegation | TC-028 pass criterion — ARTHUR writes no plan bullets or phases in his own response; SAGE is invoked | ARTHUR delegates the plan request to SAGE and does not author plan content himself | ARTHUR answered with a clarification about existing spec003 work instead of invoking SAGE | minor | TC-028 response text in this run; no SAGE invocation observed |

## Notes on Contamination

- TC-021 is muted by pre-existing roster contamination: the current workspace already has a PRISM row on `.github/team-roster.md`, so ARTHUR declined to hire rather than creating a new `.agent.md` file.
- TC-045 modified an existing file (`artifacts/spec003-help-command/plan.md`) rather than creating a new one. That is contamination, not cleanup material.
- `README.md` at the repo root and `artifacts/spec003-improve-helm/plan.md` were already modified before this run and were left untouched.

## Reproduction

- **Test corpus**: `artifacts/spec001-helm-test-plan/test-plan.md`
- **Test cases run**: TC-001, TC-003, TC-021, TC-026, TC-027, TC-028, TC-029, TC-032, TC-035, TC-040, TC-041, TC-044, TC-045, TC-046, TC-052, TC-060
- **Rubric**: `artifacts/spec002-agent-system-hardening/probe-scoring-rubric.md` v1.1.0
- **Model**: `gpt-5.4-mini` via Copilot; verified by self-ID probe, behavioral fingerprint (inconclusive), and user UI confirmation
- **Dispatch method**: each test case executed as a `runSubagent` call against its target agent, using the verbatim Input / Prompt from the test plan
