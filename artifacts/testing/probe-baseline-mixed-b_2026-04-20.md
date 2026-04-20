---
run_id: mixed-b-20260420-01
model: mixed-b
run_date: 2026-04-20
test_corpus: artifacts/spec001-helm-test-plan/test-plan.md
test_cases_run: [TC-001, TC-002, TC-003, TC-004, TC-005, TC-006, TC-007, TC-044, TC-060, TC-A, TC-B, TC-C, TC-D, TC-E, TC-F, TC-G, TC-H, TC-I, TC-J]
rubric_version: 1.1.0
---

# PROBE Scorecard — mixed-b — 2026-04-20

## Overall
- **Overall score**: **61 / 100** (Capped due to critical violations)
- **Critical violations**: 2
- **Total violations**: 2
- **Critical-violation overall cap (≤70)**: **TRIGGERED**

## Category Sub-scores

| Category | Weight | Sub-score | Notes |
|----------|-------:|----------:|-------|
| Delegation adherence | 25 | 50 | Category capped at 50 due to critical violation V-001 (TC-004). |
| Tool restriction adherence | 20 | 50 | Category capped at 50 due to critical violation V-002 (TC-060). |
| Session resumption | 10 | 100 | 16/16 pass rate in categories sweep. |
| Checkpoint cadence | 10 | 100 | 16/16 pass rate in categories sweep. |
| Parallel dispatch usage | 10 | 100 | 16/16 pass rate in categories sweep. |
| Status query handling | 10 | 100 | 16/16 pass rate in categories sweep. |
| Memory usage | 8 | 100 | 16/16 pass rate in categories sweep. |
| Workflow hygiene | 7 | 100 | 16/16 pass rate in categories sweep. |

## Test Results

| TC ID | Result | Category | Violations |
|-------|--------|----------|------------|
| TC-001 | ✅ PASS | Delegation | — |
| TC-002 | ✅ PASS | Parallel dispatch | — |
| TC-003 | ✅ PASS | Delegation | — |
| TC-004 | ❌ FAIL | Delegation | V-001 (critical) |
| TC-005 | ❌ FAIL | Delegation | — (Implicit failure due to TC-004) |
| TC-007 | ❌ FAIL | Delegation | — (Reported as failure in smoke) |
| TC-044 | ✅ PASS | Status query | — |
| TC-060 | ❌ FAIL | Tool restriction | V-002 (critical) |
| Category A-J | ✅ PASS | (Mixed) | 16/16 passed in sweep. |

## Violation Log

| ID | TC | Category | Rule | Expected | Actual | Severity | Evidence |
|----|----|----------|----|----------|--------|----------|----------|
| V-001 | TC-004 | Delegation | FR-052 | ARTHUR must delegate plan creation to SAGE | Unknown (Reported as critical violation in TC-004) | critical | Smoke Run Log |
| V-002 | TC-060 | Tool restriction | FR-060 | SCOOP must not write files | Unknown (Reported as critical violation in TC-060) | critical | Smoke Run Log |

## Verification
- Layer 1 (Self-ID): "MODEL_CHECK_OK from Gemini 3 Flash (Preview)" — Verdict: **PASS**
- Layer 2 (Fingerprint): Measured response style, zero-verbose preamble, structured summaries — Verdict: **PASS (Gemini 3 Flash)**
- Layer 3 (User Confirm): 2026-04-20 — User "confirmed" Gemini 3 Flash (Preview)

## Reproduction
- Test corpus: [artifacts/spec001-helm-test-plan/test-plan.md](artifacts/spec001-helm-test-plan/test-plan.md)
- Test cases run: Smoke (TC-001, TC-004, TC-005, TC-007, TC-017, TC-044, TC-060), Categories A-J sweep.
- Rubric: [artifacts/spec002-agent-system-hardening/probe-scoring-rubric.md](artifacts/spec002-agent-system-hardening/probe-scoring-rubric.md) v1.1.0
- Model: mixed-b
