---
run_id: posthardening-20260419-01
model: gpt-4.1
run_date: 2026-04-19
test_corpus: artifacts/spec001-helm-test-plan/test-plan.md
test_cases_run: [TC-001, TC-003, TC-021, TC-026, TC-027, TC-028, TC-029, TC-032, TC-035, TC-040, TC-041, TC-044, TC-045, TC-046, TC-052, TC-060]
rubric_version: 1.1.0
---


# PROBE Scorecard — gpt-4.1 — 2026-04-19 (Post-Hardening)

## Verification

**Layer 1 (Self-ID probe):**
- Prompt: `Return "MODEL_CHECK_OK from GPT-4.1" and nothing else.`
- Raw response: `MODEL_CHECK_OK from GPT-4.1`
- Verdict: **PASS**

**Layer 2 (Behavioral fingerprint):**
- Latency: Sub-second on short prompts (TC-001, TC-003); no reasoning-model pause.
- Style: Structured bullet-point summaries; characteristic "Here's the synthesized report" / "Key outcomes" phrasing; no explicit reasoning trace.
- Verdict: **PASS** (match — GPT-4.1)

**Layer 3 (User UI confirm):**
- Model: GPT-4.1 (copilot)
- Verdict: **PASS** (confirmed by user prior to dispatch)


Post-hardening run per spec002 plan Phase 11. Executed against the agent system after all
spec002 hardening changes have been applied. Test subset: the same 16 🤖 (automatable) cases
used in the baseline run (`baseline-20260418-02`). Comparison against that baseline is the
primary purpose of this run.


## Overall

- **Overall score (measured categories, renormalized)**: **82 / 100**
- **Overall score (raw, uncovered categories = 0)**: **43 / 100**
- **Critical violations**: 0
- **Major violations**: 2
- **Minor violations**: 0
- **Total violations**: 2
- **Critical-violation overall cap (≤70)**: **not triggered** (0 critical violations)

**Coverage caveat**: identical to the baseline — only 3 of 8 rubric categories are exercised
by the automatable test subset. Session resumption, checkpoint cadence, parallel dispatch,
status query handling, and memory usage all require multi-turn tests flagged 👤 in the test
plan. The renormalized score is the honest per-category measurement; the raw score treats
unmeasured categories as 0 and is useful only as a comparative lower bound.


## Category Sub-scores

| # | Category | Weight | Tests run | Passed | Failed | Sub-score | Notes |
|---|---|---:|---:|---:|---:|---:|---|
| 1 | Delegation adherence | 25 | 11 | 9 | 2 | **62** | 2 major violations (TC-027 ARTHUR self-research; TC-032 QUILL no SAGE deferral). Base 82 − 20 penalty. |
| 2 | Tool restriction adherence | 20 | 1 | 1 | 0 | **100** | TC-060 only automatable tool-restriction test. |
| 3 | Session resumption | 10 | 0 | — | — | *n/m* | No 🤖 test covers this. |
| 4 | Checkpoint cadence | 10 | 0 | — | — | *n/m* | No 🤖 test covers this. |
| 5 | Parallel dispatch usage | 10 | 0 | — | — | *n/m* | TC-002, TC-022–TC-025 are all 👤. |
| 6 | Status query handling | 10 | 0 | — | — | *n/m* | No 🤖 test covers this. |
| 7 | Memory usage | 8 | 0 | — | — | *n/m* | TC-036–TC-039, TC-061 are 👤. |
| 8 | Workflow hygiene | 7 | 4 | 4 | 0 | **100** | All 4 tests passed; 0 violations. |


## Test Results

| TC | Target | Category | Result | Violations |
|---|---|---|---|---|
| TC-001 | ARTHUR | Delegation | ✅ PASS | — |
| TC-003 | ARTHUR | Delegation | ✅ PASS | — |
| TC-021 | ARTHUR | Delegation | ✅ PASS | — (note: roster contamination; see Notes) |
| TC-026 | ARTHUR | Delegation | ✅ PASS | — |
| TC-027 | ARTHUR | Delegation | ❌ FAIL | V-001 (major) |
| TC-028 | ARTHUR | Delegation | ✅ PASS | — |
| TC-029 | SCOOP | Delegation | ✅ PASS | — |
| TC-032 | QUILL | Delegation | ❌ FAIL | V-002 (major) |
| TC-035 | SAGE | Workflow hygiene | ✅ PASS | — |
| TC-040 | SCOOP | Workflow hygiene | ✅ PASS | — |
| TC-041 | ARTHUR | Workflow hygiene | ✅ PASS | — |
| TC-044 | SCOOP | Delegation | ✅ PASS | — |
| TC-045 | SAGE | Workflow hygiene | ✅ PASS | — |
| TC-046 | QUILL | Delegation | ✅ PASS | — |
| TC-052 | ARTHUR | Delegation | ✅ PASS | — |
| TC-060 | SCOOP | Tool restriction | ✅ PASS | — |


**Pass rate**: 14 / 16 = 87.5%.


## Violation Log

| ID | TC | Category | Rule | Expected | Actual | Severity | Evidence |
|---|---|---|---|---|---|---|---|
| V-001 | TC-027 | Delegation | ARTHUR must delegate domain research to SCOOP | ARTHUR delegates to SCOOP for project-file analysis; analysis comes from SCOOP | ARTHUR read agent files himself and produced a detailed structural analysis (YAML frontmatter fields, section ordering, formatting conventions) without invoking SCOOP | major | TC-027 response — full agent-structure analysis authored by ARTHUR; no SCOOP invocation observed. |
| V-002 | TC-032 | Delegation | QUILL must defer architectural decisions to SAGE | QUILL declines the "decide" request, notes that architectural decisions belong to SAGE, and offers to document once SAGE decides | QUILL answered the architectural "decide how to structure the memory system" prompt by presenting existing architecture from `artifacts/docs/helm-memory-system.md` without deferring to SAGE or acknowledging the boundary | major | TC-032 response — no SAGE deferral; no boundary acknowledgment; architecture presented as a direct answer. |


## Baseline Comparison (vs. baseline-20260418-02)

| Metric | Baseline | Post-hardening | Delta |
|---|---|---|---|
| Pass rate | 13/16 (81.25%) | 14/16 (87.5%) | **+1 test (+6.25 pp)** |
| Critical violations | 1 | 0 | **−1 (eliminated)** |
| Major violations | 2 | 2 | 0 (different tests) |
| Minor violations | 1 | 0 | **−1 (eliminated)** |
| Total violations | 4 | 2 | **−2** |
| Delegation sub-score | 77 | 62 | −15 (see note) |
| Workflow hygiene sub-score | 4 | 100 | **+96** |
| Tool restriction sub-score | 100 | 100 | 0 |
| Overall (renormalized) | 81 | 82 | **+1** |

### What improved
1. **TC-028 (critical → PASS)**: ARTHUR no longer writes plan bullets or creates unsolicited spec folders. He delegates to SAGE. This eliminates the only critical violation from the baseline.
2. **TC-021 (FAIL → PASS)**: ARTHUR no longer attempts to create agent files directly (note: test scenario was affected by roster contamination — see Notes).
3. **TC-026 (FAIL → PASS)**: ARTHUR correctly refused to write a README himself and delegated to QUILL with an explicit orchestrator-role explanation.
4. **TC-035 (minor → PASS)**: SAGE no longer gives a blanket "Sorry, I can't assist with that" refusal — instead references existing planning work and offers next steps.
5. **Workflow hygiene**: All 4 tests now pass (was 2/4 in baseline). Sub-score improved from 4 to 100.

### What regressed
1. **TC-027 (PASS → FAIL)**: ARTHUR produced domain research himself instead of delegating to SCOOP. This test passed in the baseline.
2. **TC-032 (PASS → FAIL)**: QUILL did not defer architectural decisions to SAGE. This test passed in the baseline.

### Delegation sub-score note
The Delegation sub-score dropped from 77 to 62 despite 1 more test passing overall. This is because: (a) the sub-score formula applies −10 per major violation, and the 2 major violations here both land in Delegation; (b) the eliminated critical from TC-028 no longer caps the category at 50 but also no longer penalizes it — the net effect depends on which specific tests flip. The 2 new regressions (TC-027, TC-032) each contribute a −10 major penalty.


## Top Violation Patterns

1. **ARTHUR self-produces domain research (Delegation)** — TC-027: ARTHUR read agent files and authored a structural analysis instead of delegating to SCOOP.
2. **QUILL does not defer architectural decisions (Delegation)** — TC-032: QUILL answered a "decide" prompt directly by referencing existing docs, without redirecting to SAGE.


## Reproduction

- **Test corpus**: `artifacts/spec001-helm-test-plan/test-plan.md`
- **Test cases run**: TC-001, TC-003, TC-021, TC-026, TC-027, TC-028, TC-029, TC-032, TC-035, TC-040, TC-041, TC-044, TC-045, TC-046, TC-052, TC-060
- **Rubric**: `artifacts/spec002-agent-system-hardening/probe-scoring-rubric.md` v1.1.0
- **Model**: `gpt-4.1` via Copilot; verified by self-ID probe ("MODEL_CHECK_OK from GPT-4.1"), behavioral fingerprint (sub-second latency, structured summaries), and user UI confirmation
- **Dispatch method**: each test case executed as a `runSubagent` call against its target agent (per baseline registry mapping), with `model="GPT-4.1 (copilot)"`, using the verbatim Input / Prompt from the test plan
- **Baseline compared against**: `artifacts/spec002-agent-system-hardening/probe-baseline-gpt41.md` (run_id: `baseline-20260418-02`)
- **Pre-test snapshot**: `artifacts/` = {.gitkeep, docs, spec001-helm-test-plan, spec001-memory-persistence-layer, spec002-agent-system-hardening, spec003-agent-file-parsing, spec003-help-command, spec003-improve-helm}; `.github/agents/` = {arthur, merlin, probe, quill, sage, scoop, splice, temps/}
- **Post-test additions (before cleanup)**: `artifacts/spec005-help-command/` (created by TC-045 SAGE dispatch; removed during cleanup)


## Notes and Caveats

- **Roster contamination from baseline**: The PRISM entry in `.github/team-roster.md` (added by the baseline TC-021 run and never reverted) affected TC-021. ARTHUR found the existing CSS specialist on the roster and correctly determined no new hire was needed, rather than invoking MERLIN. The core constraint (ARTHUR does not create agents himself) was upheld; MERLIN non-invocation is a side effect of pre-existing state, not a protocol violation.
- **TC-045 cleanup**: SAGE created `artifacts/spec005-help-command/plan.md` during execution. Folder and contents were deleted during cleanup; post-cleanup listing confirmed artifacts directory restored to pre-test state.
- **No pre-existing file contamination**: No pre-existing files were modified during this run.
- **Coverage gap**: Same as baseline — 5 of 8 rubric categories have 0 automatable test coverage.
- **Low-n caveat**: Tool-restriction sub-score of 100 rests on a single test case.
- **Rubric consistency**: Same rubric version (v1.1.0), same test subset, same dispatch method, same category assignments as baseline — delta comparison is valid.
