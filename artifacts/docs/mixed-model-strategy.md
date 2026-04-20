# Mixed-Model Strategy — Helm AI Team Model Assignment

*Last updated: 2026-04-19 | Active rubric: v1.1.0 | Author: QUILL*

---

## 1. Overview

This document guides `model:` frontmatter assignment for each Helm AI team agent across four cost/quality scenarios. The target reader is the workspace owner applying changes directly to `.agent.md` files.

### Who this is for

You have a working Helm agent system (post-spec002 hardening) and want to understand which AI model to back each agent with — and why — given your current cost tolerance.

### Data sources, in reliability order

| # | Source | Confidence | What it provides |
|---|---|---|---|
| 1 | **PROBE test results** | Highest | Behavioral test scores from 16 automatable test cases against the hardened system. All post-hardening except Gemini 3 Flash and GPT-5.4 mini (first-time baselines). |
| 2 | **Copilot cost tiers** (`models_list20260419.md`) | High | Verified cost multipliers per model as of 2026-04-19. |
| 3 | **model_comparison.md** | Moderate | Internet-researched capability ratings per functional domain (High/Medium/Low). Not empirically validated against the Helm task profile. |

### How to read this document

- **Sections 3–6** each cover one scenario: assignment table, rationale, caveats, and estimated quality.
- **Section 7** compares all four scenarios side-by-side with per-agent cost multipliers.
- **Section 9** is the copy-paste reference for `.agent.md` frontmatter.
- **ARTHUR carries no `model:` frontmatter in any scenario.** ARTHUR is the orchestrator and always follows the VS Code model picker selection. Each scenario includes a **recommended picker setting** — the model you should have selected in the VS Code model picker when using that scenario. This is not a frontmatter edit; it is a manual picker change before you begin a session.
- **PROBE carries a fixed `model: "Claude Sonnet 4.6 (copilot)"` frontmatter in all scenarios.** PROBE is the measurement instrument, not a subject under test. A constant evaluator model is required to prevent PROBE's evaluation quality from confounding cross-scenario test result comparisons.

---

## 2. Model Reference Table

Candidate models for Helm agent assignment. GPT-4.1 is listed for historical context only. Claude Sonnet 4.6 is excluded from cost-constrained scenarios (A, B, D) but is included in Scenario C (best of the best, cost-no-object). Claude Haiku 4.5 is included in B and D for low-demand roles.

| Model | Helm Score | Pass Rate | Cost Tier | Multi-agent | Research | Reasoning | Coding | Notes |
|---|---|---|---|---|---|---|---|---|
| GPT-5 mini | 80/100 | 13/16 (81.3%) | **0x** | 🟡 Medium | 🟡 Medium | 🟢 High | 🟡 Medium | Post-hardening; 0 critical violations; best validated 0-cost option |
| Raptor mini (Preview) | — | — | **0x** | 🔴 Low | 🔴 Low | 🔴 Low | 🟢 High | No Helm test data; useful only for coding-specific roles |
| Grok Code Fast 1 | — | — | **0.25x** | 🟡 Medium | 🔴 Low | 🔴 Low | 🟢 High | No Helm test data; coding specialist at near-zero cost |
| Gemini 3 Flash (Preview) | 76/100† | 13/16 (81.3%) | **0.33x** | 🟢 High | 🟢 High | 🟢 High | 🟢 High | †Tested on rubric v1.0.0 — directionally comparable, not directly equivalent to v1.1.0 scores; 0 critical violations |
| GPT-5.4 mini | 70/100‡ | 11/16 (68.8%) | **0.33x** | 🟢 High | 🟡 Medium | 🟢 High | 🟢 High | ‡Score cap triggered on TC-026 (delegation boundary); caveat is ARTHUR-role specific — see note below |
| Claude Haiku 4.5 | — | — | **0.33x** | 🟡 Medium | 🟡 Medium | 🔴 Low | 🟡 Medium | No Helm test data; Low reasoning disqualifies it from planning or research roles |
| GPT-4.1 | 82/100 | 14/16 (87.5%) | 0x | 🟢 High | 🟢 High | 🟢 High | 🟢 High | **DEPRECATED — do not assign to any agent** |
| Claude Sonnet 4.6 | 82/100 | 14/16 (87.5%) | **1x** | 🟡 Medium | 🟡 Medium | 🟢 High | — | Best tested Helm score tied with GPT-4.1. Excluded from cost-constrained scenarios (A/B/D); eligible for Scenario C. |
| Claude Opus 4.5 | — | — | **3x** | 🟢 High | 🟢 High | 🟢 High | — | No Helm test data. Expected to exceed Sonnet 4.6's 82/100 based on tier; suitable for Scenario C only. |
| Claude Opus 4.6 | — | — | **3x** | 🟢 High | 🟢 High | 🟢 High | — | No Helm test data. Same generation as Sonnet 4.6 at Opus tier; best expected research + reasoning for premium budget. |
| Claude Opus 4.7 | — | — | **7.5x** | 🟢 High | 🟢 High | 🟢 High | — | No Helm test data. Top of the Claude tier as of 2026-04-19. Scenario C only; cost warrants deliberate justification. |

> **Rubric caveat (†):** Gemini 3 Flash was tested on rubric v1.0.0. The v1.1.0 rubric added TC-026 (delegation boundary) and adjusted category weights. Gemini 3 Flash's 76/100 is directionally comparable but not directly equivalent to GPT-5 mini's 80/100 or GPT-5.4 mini's 70/100.

> **TC-026 caveat (‡):** GPT-5.4 mini's score cap was triggered by TC-026, which tests whether the orchestrator (ARTHUR) directly produces deliverables. This violation cannot be triggered by non-orchestrator agents (SAGE, QUILL, MERLIN, PROBE, SPLICE) — they are the recipients of delegation, not the dispatchers. GPT-5.4 mini's 11/16 pass rate still reflects 4 failures outside TC-026, so the score should not be read as equivalent to a non-capped 80+ result.

> **Note on standard-tier models:** Claude Sonnet 4.6 (1x) has been run against the Helm behavioral test suite (82/100, rubric v1.1.0). All other models at 1x cost and above (Claude Opus 4.5/4.6/4.7, GPT-5.4, GPT-5.2, GPT-5.3-Codex, Gemini 2.5 Pro, Gemini 3.1 Pro) have not been tested against the Helm suite and are not characterized in model_comparison.md. They are referenced in Scenario C with explicit caveats.

---

## 3. Scenario A — 0-Cost Roster

**Constraint:** 0x cost models only. GPT-4.1 excluded (deprecated). Available: GPT-5 mini, Raptor mini (Preview).

| Agent | Assigned Model | Rationale |
|---|---|---|
| **ARTHUR** | **Picker: `GPT-5 mini`** | Only tested 0x model not deprecated; 80/100 Helm score includes ARTHUR-role delegation tests (TC-001, TC-003, TC-021, TC-026, TC-027, TC-028, TC-040, TC-052). Medium multi-agent is the 0x ceiling — acceptable for this scenario. |
| SCOOP | `GPT-5 mini (copilot)` | Only viable 0x option; Medium research is the ceiling at this tier; High reasoning supports synthesis after web retrieval |
| SAGE | `GPT-5 mini (copilot)` | Best tested 0x model (80/100, 0 critical violations); High reasoning/planning per model_comparison |
| QUILL | `GPT-5 mini (copilot)` | Structured prose and consistent formatting well within tested capability |
| MERLIN | `GPT-5 mini (copilot)` | Procedural agent creation and roster management do not require advanced research capability |
| **PROBE** | `Claude Sonnet 4.6 (copilot)` | Fixed evaluator — same model in all scenarios; prevents evaluation quality from confounding cross-scenario test results. |
| SPLICE | `Raptor mini (Preview) (copilot)` | High coding per model_comparison; Low multi-agent is acceptable for a coding-only temp agent taking direct instructions |

**Quality estimate:** GPT-5 mini's 80/100 tested score is the ceiling for SCOOP, SAGE, QUILL, and MERLIN. Raptor mini introduces uncertainty — no Helm baseline exists for SPLICE. SCOOP is the weakest point: Medium research is a real constraint for complex investigation tasks.

**Caveats:**
- Raptor mini has no Helm test data. Run a PROBE coding baseline before relying on SPLICE in production use.
- SCOOP's research quality is limited at Medium. Expect lower fidelity on research tasks that require deep synthesis or cross-source corroboration.
- This is the minimum-cost viable configuration. Quality tradeoffs are real.

---

## 4. Scenario B — Low-Cost Roster

**Constraint:** 0x and 0.33x tiers. Grok Code Fast 1 (0.25x) permitted for coding agents. Available: GPT-5 mini (0x), Raptor mini (0x), Gemini 3 Flash (Preview) (0.33x), GPT-5.4 mini (0.33x), Claude Haiku 4.5 (0.33x), Grok Code Fast 1 (0.25x).

| Agent | Assigned Model | Cost | Rationale |
|---|---|---|---|
| **ARTHUR** | **Picker: `Gemini 3 Flash (Preview)`** | 0.33x | High multi-agent + delegation + 1M context; best available model for orchestration at this tier. ARTHUR initiates every interaction — 1M context prevents context truncation on long multi-agent sessions better than any 0x option. |
| SCOOP | `Gemini 3 Flash (Preview) (copilot)` | 0.33x | Only model in this tier rated High for research; 1M context window directly benefits deep investigation tasks; 13/16 pass rate (same as GPT-5 mini) on a comparable rubric |
| SAGE | `GPT-5.4 mini (copilot)` | 0.33x | High reasoning + planning per model_comparison; TC-026 cap is ARTHUR-role specific and does not apply when the model is playing SAGE; most spend-justified upgrade from GPT-5 mini within this tier |
| QUILL | `GPT-5 mini (copilot)` | 0x | Documentation task demands are within GPT-5 mini's tested capability; no 0.33x model offers a clear improvement for structured prose |
| MERLIN | `GPT-5 mini (copilot)` | 0x | Procedural agent creation and roster management do not justify 0.33x spend; no identified quality gap |
| **PROBE** | `Claude Sonnet 4.6 (copilot)` | 1x | Fixed evaluator — same model in all scenarios; prevents evaluation quality from confounding cross-scenario test results. |
| SPLICE | `Grok Code Fast 1 (copilot)` | 0.25x | High coding at near-zero incremental spend over Raptor mini; explicitly listed as permitted for coding agents in this tier |

**Quality estimate:** Meaningful improvement over Scenario A for the two highest-impact agents — SCOOP gains High research capability and 1M context; SAGE gains a model with High reasoning/planning specifically. QUILL, MERLIN, and SPLICE hold or improve at equal or lower relative cost.

**Caveats:**
- Gemini 3 Flash's Helm score is on rubric v1.0.0. TC-026 was not part of that rubric — its delegation-boundary behavior is untested. Assign to SCOOP (not an orchestrator role) to minimize exposure to this gap.
- GPT-5.4 mini's 70/100 cap score does not represent its SAGE-role performance. The TC-026 violation cannot fire when the model is playing SAGE. However, it did fail 4 other test cases (11/16 pass rate vs. 13/16 for GPT-5 mini). Treat this assignment as provisional pending a SAGE-specific PROBE validation.
- Claude Haiku 4.5 (0.33x) was evaluated for QUILL and MERLIN but not assigned — GPT-5 mini at 0x has a tested 80/100 score while Haiku has no Helm baseline, making the 0.33x spend unjustified at this time. Run a Haiku baseline before reconsidering.
- Grok Code Fast 1 has no Helm test data. Run a PROBE coding baseline before treating SPLICE as fully validated.

---

## 5. Scenario C — Best of the Best

**Constraint:** None. Select highest-performing model for each agent's specific task profile.

> **Important:** Most standard-tier models in this scenario have not been run against the Helm behavioral test suite. Exception: Claude Sonnet 4.6 (1x) has a validated Helm score of 82/100 (14/16, 0 critical violations, rubric v1.1.0) and is the recommended picker for ARTHUR. (PROBE uses Claude Sonnet 4.6 as its fixed evaluator frontmatter in all scenarios — not specific to Scenario C.) Claude Opus 4.6 (3x, SCOOP and SAGE) and GPT-5.3-Codex (1x, SPLICE) have no Helm test data — those assignments reflect capability extrapolation. Run PROBE baselines before treating Scenario C as fully validated.

| Agent | Assigned Model | Cost | Rationale |
|---|---|---|---|
| **ARTHUR** | **Picker: `Claude Sonnet 4.6`** | 1x | Highest tested Helm score at 82/100 (14/16 pass rate, 0 critical violations); outperforms GPT-5.4 mini's capped 70/100 in orchestration. Validated against ARTHUR-role delegation tests — the only standard-tier model with empirical Helm data for this role. |
| SCOOP | `Claude Opus 4.6 (copilot)`¹ | 3x | Strongest available research + reasoning model with direct generational lineage to our tested Sonnet 4.6 (82/100). Same-generation extrapolation is more reliable than cross-vendor projection to Gemini 3.1 Pro. |
| SAGE | `Claude Opus 4.6 (copilot)`¹ | 3x | Highest-confidence pick for planning-intensive work given Sonnet 4.6's validated 82/100 score; same-generation relationship makes performance extrapolation more reliable than GPT-5.4. No TC-026 constraint for SAGE role. |
| QUILL | `GPT-5 mini (copilot)` | 0x | Structured documentation is reliably within GPT-5 mini's tested 80/100 capability; no standard-tier model offers evidence of meaningfully better doc output in available data |
| MERLIN | `GPT-5 mini (copilot)` | 0x | Procedural tasks (agent creation, roster management) are well within tested scope; no quality gap identified that standard tier would close |
| **PROBE** | `Claude Sonnet 4.6 (copilot)` | 1x | Fixed evaluator — same model in all scenarios; prevents evaluation quality from confounding cross-scenario test results. |
| SPLICE | `GPT-5.3-Codex (copilot)`¹ | 1x | Purpose-built coding model at standard tier; expected to outperform general-purpose models on targeted surgical code changes |

*¹ No Helm PROBE test data. Verify exact VS Code frontmatter name from the model picker UI before use — these names are not confirmed in models_list20260419.md.*

**Quality estimate:** ARTHUR uses Claude Sonnet 4.6 via picker (82/100 Helm tested, 0 critical violations) — the highest empirically validated orchestration score in the dataset. PROBE uses Claude Sonnet 4.6 via fixed frontmatter, consistent with all other scenarios. SCOOP and SAGE use Claude Opus 4.6 (no Helm test data, but same-generation extrapolation from Sonnet 4.6 is more reliable than cross-vendor projection). QUILL and MERLIN hold at GPT-5 mini (80/100 tested). SPLICE remains aspirational at standard tier until a PROBE coding baseline exists.

**Caveats:**
- Claude Opus 4.6 and GPT-5.3-Codex frontmatter names are not confirmed in models_list20260419.md. Verify exact names from the VS Code model picker before writing frontmatter. An unrecognized model name in frontmatter causes the agent to silently fall back to the picker default.
- Claude Sonnet 4.6 is the ARTHUR picker model — verify the exact picker name in VS Code before beginning a session.
- The practical ceiling backed by Helm test data is Claude Sonnet 4.6 (82/100) for ARTHUR (picker) and PROBE (fixed frontmatter), and GPT-5 mini (80/100) for QUILL/MERLIN. Scenario D remains the more actionable recommendation until Claude Opus 4.6 baselines exist.

---

## 6. Scenario D — Best Blend *(Recommended)*

**Strategy:** Assign tested high performers to the roles with the most downstream impact on system quality (SCOOP, SAGE). Use cost-effective tested models for supporting roles (QUILL, MERLIN). Reserve spend only where data justifies the delta.

| Agent | Assigned Model | Cost | Rationale |
|---|---|---|---|
| **ARTHUR** | **Picker: `Gemini 3 Flash (Preview)`** | 0.33x | High multi-agent + delegation + 1M context; best available tested model for orchestration. ARTHUR processes the longest combined context (full session + all subagent briefs) — the 1M context window is the highest-value differentiator for the orchestrator role specifically. |
| SCOOP | `Gemini 3 Flash (Preview) (copilot)` | 0.33x | Best-tested research model with available data (High research, 1M context, 13/16 pass rate); rubric caveat accepted for SCOOP role — TC-026 is ARTHUR-specific and cannot fire here |
| SAGE | `GPT-5 mini (copilot)` | 0x | Best overall Helm behavioral score in the validated set (80/100, 0 critical violations, 13/16 pass rate); High reasoning/planning in model_comparison; spend is preserved without a validated quality delta to justify GPT-5.4 mini |
| QUILL | `GPT-5 mini (copilot)` | 0x | Tested and sufficient; structured documentation is reliably within 80/100 capability |
| MERLIN | `GPT-5 mini (copilot)` | 0x | Procedural HR tasks are within tested scope; no quality gap at 0x |
| **PROBE** | `Claude Sonnet 4.6 (copilot)` | 1x | Fixed evaluator — same model in all scenarios; prevents evaluation quality from confounding cross-scenario test results. |
| SPLICE | `Grok Code Fast 1 (copilot)` | 0.25x | High coding at near-zero incremental cost over Raptor mini; better code specialization than GPT-5 mini at minimal spend delta |

**Quality estimate:** Highest expected quality/cost ratio of all four scenarios. SCOOP and SAGE handle the highest-stakes work; both are assigned the best available model for their specific demand profile. QUILL and MERLIN are adequately served at 0x. PROBE is fixed at 1x (Claude Sonnet 4.6) regardless of scenario.

**Why not GPT-5.4 mini for SAGE?** GPT-5.4 mini has High reasoning/planning in model_comparison.md. However, its 11/16 pass rate across the full Helm suite (versus 13/16 for GPT-5 mini) reflects 4 behavioral failures outside TC-026. Without a SAGE-specific PROBE validation run to confirm those failures don't occur in planning contexts, GPT-5 mini's higher tested alignment is the more conservative and better-evidenced choice. Revisit after a targeted PROBE run.

**Caveats:**
- Gemini 3 Flash Helm score is on rubric v1.0.0. Re-running on v1.1.0 is the highest-priority next action — until then, this assignment carries the rubric-version caveat.
- Grok Code Fast 1 has no Helm test data for SPLICE. Run a PROBE coding baseline before treating this as fully validated.
- Claude Haiku 4.5 (0.33x) was evaluated for QUILL and MERLIN but GPT-5 mini's tested 80/100 score at 0x makes the spend unjustifiable without a Haiku Helm baseline. If a Haiku baseline shows 80+ with 0 critical violations, it becomes a viable alternative for QUILL/MERLIN in the Blend scenario.

---

## 7. Scenario Comparison

### Agent assignments across all scenarios

| Agent | Scenario A (0x) | Scenario B (low-cost) | Scenario C (best) | Scenario D (recommended) |
|---|---|---|---|---|
| **ARTHUR (picker)** | **`GPT-5 mini (copilot)`** | **`Gemini 3 Flash (Preview) (copilot)`** | **`Claude Sonnet 4.6 (copilot)`** | **`Gemini 3 Flash (Preview) (copilot)`** |
| SCOOP | `GPT-5 mini (copilot)` | `Gemini 3 Flash (Preview) (copilot)` | `Claude Opus 4.6 (copilot)`¹ | `Gemini 3 Flash (Preview) (copilot)` |
| SAGE | `GPT-5 mini (copilot)` | `GPT-5.4 mini (copilot)` | `Claude Opus 4.6 (copilot)`¹ | `GPT-5 mini (copilot)` |
| QUILL | `GPT-5 mini (copilot)` | `GPT-5 mini (copilot)` | `GPT-5 mini (copilot)` | `GPT-5 mini (copilot)` |
| MERLIN | `GPT-5 mini (copilot)` | `GPT-5 mini (copilot)` | `GPT-5 mini (copilot)` | `GPT-5 mini (copilot)` |
| **PROBE (fixed)** | `Claude Sonnet 4.6 (copilot)` | `Claude Sonnet 4.6 (copilot)` | `Claude Sonnet 4.6 (copilot)` | `Claude Sonnet 4.6 (copilot)` |
| SPLICE | `Raptor mini (Preview) (copilot)` | `Grok Code Fast 1 (copilot)` | `GPT-5.3-Codex (copilot)`¹ | `Grok Code Fast 1 (copilot)` |

*¹ No Helm PROBE test data. Standard-tier frontmatter names require verification.*

### Estimated cost index per agent dispatch

| Agent | Scenario A | Scenario B | Scenario C | Scenario D |
|---|---|---|---|---|
| **ARTHUR (picker)** | **0x** | **0.33x** | **1x** | **0.33x** |
| SCOOP | 0x | 0.33x | 3x | 0.33x |
| SAGE | 0x | 0.33x | 3x | 0x |
| QUILL | 0x | 0x | 0x | 0x |
| MERLIN | 0x | 0x | 0x | 0x |
| **PROBE (fixed)** | **1x** | **1x** | **1x** | **1x** |
| SPLICE | 0x | 0.25x | 1x | 0.25x |
| **Avg (all agents)** | **~0.14x** | **~0.32x** | **~1.29x** | **~0.27x** |

PROBE's fixed 1x cost (Claude Sonnet 4.6) is uniform across all scenarios — only the agent-model choices drive scenario cost differences. Among the variable assignments, Scenario D achieves the best quality/cost ratio by keeping SAGE at 0x (GPT-5 mini tested score justifies this) and reserving Gemini 3 Flash for SCOOP and ARTHUR where context depth matters most. Scenario C's elevated cost (~1.29x avg) reflects premium Claude models for SCOOP and SAGE — justified only when Opus 4.6 baselines exist or research and planning quality are the critical constraint.

### Helm test score by assigned model

| Agent | Score (A) | Score (B) | Score (C) | Score (D) |
|---|---|---|---|---|
| SCOOP | 80 (`GPT-5 mini (copilot)`) | 76† (`Gemini 3 Flash (Preview) (copilot)`) | —¹ (`Claude Opus 4.6 (copilot)`) | 76† (`Gemini 3 Flash (Preview) (copilot)`) |
| SAGE | 80 (`GPT-5 mini (copilot)`) | 70‡ (`GPT-5.4 mini (copilot)`) | —¹ (`Claude Opus 4.6 (copilot)`) | 80 (`GPT-5 mini (copilot)`) |
| QUILL | 80 (`GPT-5 mini (copilot)`) | 80 (`GPT-5 mini (copilot)`) | 80 (`GPT-5 mini (copilot)`) | 80 (`GPT-5 mini (copilot)`) |
| MERLIN | 80 (`GPT-5 mini (copilot)`) | 80 (`GPT-5 mini (copilot)`) | 80 (`GPT-5 mini (copilot)`) | 80 (`GPT-5 mini (copilot)`) |
| SPLICE | — (`Raptor mini (Preview) (copilot)`) | — (`Grok Code Fast 1 (copilot)`) | —¹ (`GPT-5.3-Codex (copilot)`) | — (`Grok Code Fast 1 (copilot)`) |

*† Rubric v1.0.0 — not directly equivalent to v1.1.0 scores*
*‡ Cap triggered by TC-026 (ARTHUR-role specific)*
*¹ No Helm test data*

The validated score advantage of Scenario D over B for SAGE (80 vs. 70‡) is the core justification for the Best Blend recommendation.

---

## 8. Additional Recommendations

### High priority

**1. Re-run Gemini 3 Flash on rubric v1.1.0.**
The current Helm score (76/100) was on v1.0.0, which did not include TC-026 (delegation boundary) and used different category weights. A v1.1.0 re-run is the single highest-value action — it directly removes the primary caveat on SCOOP assignments in Scenarios B, C, and D.

**2. Run a SAGE-specific PROBE validation for GPT-5.4 mini.**
The TC-026 cap on GPT-5.4 mini is ARTHUR-role specific. A SAGE-profile PROBE run (planning, spec writing, task decomposition test cases) would determine whether its 4 non-TC-026 failures are role-relevant. If they are not, GPT-5.4 mini becomes a justified upgrade for SAGE in Scenario B.

**3. Run Grok Code Fast 1 baseline for SPLICE.**
Assigned in Scenarios B and D without Helm test data. Its coding specialization is plausible, but a PROBE coding test should validate before treating these scenarios as fully verified.

### Medium priority

**4. Run Raptor mini baseline for SPLICE.**
Assigned in Scenario A without test data. Low multi-agent is acceptable for a coding-only temp, but a PROBE run would confirm there are no behavioral surprises in the Helm agent context.

**5. Run standard-tier baselines before promoting Scenario C.**
GPT-5.4, Gemini 3.1 Pro, and GPT-5.3-Codex are assigned in Scenario C based on general reputation, not Helm validation. A single PROBE run per model is sufficient to either confirm the assignment or redirect to a better option.

**6. Run Claude Haiku 4.5 baseline.**
It's at 0.33x cost — same tier as Gemini 3 Flash and GPT-5.4 mini — and was not assigned to any scenario due to Low reasoning in model_comparison.md. A PROBE baseline would either confirm the disqualification or reveal viable roles (QUILL, MERLIN) where its reasoning ceiling doesn't matter.

### Notes on VS Code model features

**7. VS Code supports model arrays for fallback.**
The `model:` frontmatter field supports array syntax for fallback priority chains. Once frontmatter array support is confirmed in your VS Code version, consider configuring a fallback for SCOOP: `Gemini 3 Flash → GPT-5 mini`. This handles availability gaps without degrading to the user's picker selection.

**8. Document the picker model for each PROBE run.**
ARTHUR and PROBE follow the VS Code model picker selection. Test runs on different picker selections are not directly comparable. Begin recording the active picker model in PROBE run headers alongside the rubric version tag. This makes future model comparisons on the orchestrator path reproducible.

**9. Treat this as a living document — re-run baselines periodically.**
AI models receive silent updates from their providers. A model that scored 76/100 today may score higher or lower after an update. Recommended cadence: run the full 16-case automatable PROBE suite against each assigned model whenever a model update is announced, or at a regular interval (e.g., monthly). Update the scenario assignments in this document when a re-run produces a meaningfully different result (>5 point delta or a new critical violation). Tag each PROBE scorecard with the run date so regressions are traceable.

---

## 9. Frontmatter Quick Reference

**ARTHUR** carries no `model:` frontmatter — it always follows the VS Code model picker selection. Each scenario specifies a **Recommended Picker Setting** for ARTHUR.

**PROBE** carries `model: "Claude Sonnet 4.6 (copilot)"` **in all scenarios** — this is already applied to `probe.agent.md` and does not change between scenarios. A fixed evaluator model ensures cross-scenario test results are not confounded by evaluation quality differences.

For all other agents, add the `model:` field to the YAML frontmatter block inside the `---` fences at the top of each `.agent.md` file.

### Scenario A — 0-Cost

**Recommended Picker (ARTHUR):** `GPT-5 mini (copilot)`

```yaml
# PROBE — do not change; fixed across all scenarios
model: "Claude Sonnet 4.6 (copilot)"

# SCOOP, SAGE, QUILL, MERLIN
model: "GPT-5 mini (copilot)"

# SPLICE
model: "Raptor mini (Preview) (copilot)"
```

### Scenario B — Low-Cost

**Recommended Picker (ARTHUR):** `Gemini 3 Flash (Preview) (copilot)`

```yaml
# PROBE — do not change; fixed across all scenarios
model: "Claude Sonnet 4.6 (copilot)"

# SCOOP
model: "Gemini 3 Flash (Preview) (copilot)"

# SAGE
model: "GPT-5.4 mini (copilot)"

# QUILL, MERLIN
model: "GPT-5 mini (copilot)"

# SPLICE
model: "Grok Code Fast 1 (copilot)"
```

### Scenario C — Best of the Best

**Recommended Picker (ARTHUR):** `Claude Sonnet 4.6 (copilot)`

```yaml
# PROBE — do not change; fixed across all scenarios
model: "Claude Sonnet 4.6 (copilot)"

# SCOOP, SAGE — verify exact name in VS Code model picker
model: "Claude Opus 4.6 (copilot)"

# QUILL, MERLIN
model: "GPT-5 mini (copilot)"

# SPLICE — verify exact name in VS Code model picker before use
model: "GPT-5.3-Codex (copilot)"
```

### Scenario D — Best Blend *(Recommended)*

**Recommended Picker (ARTHUR):** `Gemini 3 Flash (Preview) (copilot)`

```yaml
# PROBE — do not change; fixed across all scenarios
model: "Claude Sonnet 4.6 (copilot)"

# SCOOP
model: "Gemini 3 Flash (Preview) (copilot)"

# SAGE, QUILL, MERLIN
model: "GPT-5 mini (copilot)"

# SPLICE
model: "Grok Code Fast 1 (copilot)"
```

---

*This document reflects data available as of 2026-04-19. Re-evaluate after each PROBE baseline run or when new models become available in the Copilot model picker.*
