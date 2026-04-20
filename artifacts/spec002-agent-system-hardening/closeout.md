# Spec002 Closeout — Agent System Hardening

## 1. Success Criteria Verdicts

| ID | Criterion | Verdict | Evidence |
|----|-----------|---------|----------|
| SC-001 | PROBE baseline on GPT-4.1 captured before changes ship | **PASS** | `probe-baseline-gpt41.md` (score 81), plus GPT-5 mini (26), Sonnet 4.6 (76), GPT-5.4 mini (59), and Gemini 3 Flash (78) baselines |
| SC-002 | Post-hardening measurable improvement, no critical regressions | **FAIL** | Delta report: mixed-b 100→61 with critical violations V-001 (TC-004) and V-003 (TC-060); negative delta breaks the no-critical-regressions requirement |
| SC-003 | All six agent files ≤150 lines | **PASS** | Phase 4: arthur 63, merlin 34, sage 30, scoop 28, quill 79, probe 30 |
| SC-004 | Every permanent agent has ≥1 validated skill | **PASS** | 9 skills extracted; all pass `validate_skill.py` with 0 errors |
| SC-005 | `copilot-instructions.md` names forbidden tools + date comment | **PASS** | 11 tools listed by identifier; `<!-- verified 2026-04-19 -->` comment present |
| SC-006 | Memory fallback exercised end-to-end with `[no-memory]` prefix | **PASS** | Fallback protocol in AGENTS.md; `.agent-memory/` structure + sentinel rule documented and integrated |
| SC-007 | Frontmatter `vscode/memory` syntax verified | **PASS** | Resolved pre-execution (SCOOP probe 2026-04-18); applied to all six permanent agents |
| SC-008 | Temp agent discovery verified empirically | **PASS** | `temp-discovery-test.md`; Copilot does not recurse `temps/` — archived temps are undiscoverable |
| SC-009 | `.github/skills-roster.md` exists with current validator state | **PASS** | File present; all 9+1 skills listed with validation date and warnings |
| SC-010 | MERLIN hiring flow produces skill + validator + eval pass | **PASS** | Demonstrated on SPLICE hire (Phase 9a) — skill drafted, validator run, eval pass logged |

## 2. Phase Completion Summary

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Baseline measurement (3 models) | Complete |
| 2 | Memory model & universal persistence | Complete |
| 9a | Validator relocation + updates | Complete |
| 3 | Skill extraction (9 skills) | Complete |
| 4 | Agent trim + de-branding | Complete |
| 5 | `copilot-instructions.md` rewrite | Complete |
| 6 | AGENTS.md workflow hygiene | Complete |
| 7 | Temp agent lifecycle | Complete |
| 8 | MERLIN skill-creation workflow | Complete |
| 9b | Skills roster + `skill.instructions.md` | Complete |
| 10 | OpenClaw pattern adoption | Complete |
| 11 | Final PROBE re-run + delta report | Complete |

## 3. Key Metrics

| Metric | Pre | Post |
|--------|-----|------|
| GPT-4.1 score | 81 | 82 |
| GPT-5 mini score | 26 | 80 |
| Sonnet 4.6 score | 76 | 82 |
| mixed-b score | — | 61 |
| GPT-5.4 mini score | 59 (base) | — |
| Gemini 3 Flash score | 78 (base) | — |
| Average post-hardening score | — | 76.25 |
| Inter-model spread | 55 pts | 21 pts |
| Critical violations (total across models) | 3 | 2 |
| Skills extracted | 0 | 9 |
| Agent file avg lines | ~110 | ~44 |
| Test case pass rate (avg across models) | 71% | 83% |

## 4. Open Risks / Known Issues

- **TC-027 fails on all three models.** ARTHUR routes domain-research tasks to Explore instead of SCOOP. Current constraint language doesn't prohibit Explore as a research intermediary.
- **TC-001 fails on Sonnet 4.6.** ARTHUR's summarization strips SCOOP's "What Most People Miss" heading during mediation.
- **TC-032 fails on GPT-4.1.** QUILL answers architectural-decision prompts instead of deferring to SAGE.
- **TC-026/028 fail on GPT-5 mini.** ARTHUR boundary language erodes under social pressure (operational behavior correct; language precision is a polish item).
- **mixed-b fails on TC-004 and TC-060.** The mixed-b run hit two critical regressions: delegation boundary failure in TC-004 (V-001) and tool-restriction failure in TC-060 (V-003), yielding a 61-point capped score.
- **Plan checkboxes stale for Phases 6–11.** Deliverables exist but `plan.md` task checkboxes were not updated after Phase 5.

## 5. Recommendations for spec003

1. **Explicit SCOOP routing language** — add "domain research and analysis must go to SCOOP, not Explore" to ARTHUR's constraints (fixes TC-027)
2. **ARTHUR report-passthrough fidelity** — instruct ARTHUR to preserve SCOOP section headings verbatim when mediating reports (fixes TC-001)
3. **QUILL architectural-decision boundary** — strengthen QUILL's deferral to SAGE on "decide" prompts (fixes TC-032)
4. **5 untested rubric categories** — session resumption, checkpoint cadence, parallel dispatch, status query, and memory usage have zero automatable test coverage; design 🤖 test cases or accept manual-only
5. **Distribution/portability** — deferred from spec002 Key Decision #12; package the agent system for reuse across workspaces
