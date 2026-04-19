# P3-T3b Eval-Pass Walkthrough — `design-test-rubric` skill

Logical walkthrough verifying that each eval prompt, when handled by PROBE loading the `design-test-rubric` skill, produces behaviour that matches both the skill's guidance and the source `probe-scoring-rubric.md` — confined to rubric design (execution content lives in the parallel `run-test-plan` skill).

## Eval 1 — `design-rubric-for-memory-discipline`

**Prompt:** "Design a scoring rubric for testing memory-scope discipline … eight categories with weights summing to 100, severity taxonomy, violation-log schema, scorecard template, and a three-layer model-verification section. Assume GPT-4.1's dominant failure mode is writing session-scope notes to /memories/ (user scope)."

**Skill-directed behaviour:**
1. Category & Weight Design: Rule "weights reflect observed failure modes" → memory-scope selection gets top weight; a second adjacent category (fallback behaviour or scope-boundary discipline) gets the #2 weight. Top two absorb 40–50%. Every row carries a one-sentence rationale. Total row present and explicit at 100.
2. Severity Taxonomy Design: critical/major/minor with the exact sub-score impacts (cap 50 / -10 / -2 with floor 0) and the hard 70/100 overall ceiling on any critical violation.
3. Violation Log Schema: all eight required fields listed with types; severity enum includes `unclassified`.
4. Run Tagging Conventions: YAML block with run_id, model, run_date, test_corpus, test_cases_run, rubric_version.
5. Model Execution Verification: Layer 1 prompt verbatim; Layer 2 fingerprint rows for `gpt-4.1` and `claude-sonnet-4.6` (both present in the skill's canonical list); Layer 3 user-UI confirm handoff prompt verbatim.
6. Scorecard Template: exact section list (Overall / Category Sub-scores / Test Results / Violation Log / Verification / Reproduction).
7. Versioning: 1.0.0 stamp with a dated changelog entry per the "every version bump carries a one-line changelog entry" rule.

**Cross-check against `probe-scoring-rubric.md`:**
- §2 Categories and Weights: the source rubric's total row, one-sentence rationale discipline, and top-two clustering (Delegation 25 + Tool restriction 20 = 45%) is the exact pattern the skill requires.
- §3 Severity Classification: critical-cap-50 / major-minus-10 / minor-minus-2 / overall-ceiling-70 match verbatim.
- §4 Violation Log Schema: the eight-field table (id/test_case_id/category/rule_violated/expected/actual/severity/evidence) matches.
- §5 Test-Run Tagging: YAML block fields match the skill's run-tagging section.
- §7 Model Execution Verification: three-layer protocol, fingerprint table shape, and flagging rules are lifted from v1.1.0 of the source rubric.

**Expectations satisfied:** all five (eight-category/weight-100, top-two clustering + rationale, severity taxonomy with overall-ceiling, full violation-log schema with `unclassified`, scorecard + three-layer verification + v1.0.0 with changelog).

## Eval 2 — `add-severity-categorization-to-existing-rubric`

**Prompt:** "The existing rubric … already defines eight categories and weights. Review it and add a severity taxonomy section … bump the rubric version and append a changelog entry."

**Skill-directed behaviour:**
1. Severity Taxonomy Design section dictates the exact tiers and impacts to add: critical (cap 50), major (-10 floor 0), minor (-2 floor 0), plus the 70/100 overall ceiling on critical.
2. Rule "assign severity by consequence, not by effort" is reproduced in the added section — no grading-by-output-merit language.
3. Rule "if no rule covers the behaviour, severity is `unclassified`" → the added section includes the `unclassified` escape hatch and the author-owned decision path (extend taxonomy → minor version bump).
4. Versioning section dictates: minor bump (1.0.0 → 1.1.0) + one-line dated changelog entry.
5. Freeze vs revise rules prevent altering category weights as part of a severity addition (the two are orthogonal).

**Cross-check against `probe-scoring-rubric.md`:**
- The source rubric's v1.1.0 entry is already the severity addition in its own history; the skill-directed behaviour regenerates that exact change from scratch on a counterfactual v1.0.0.
- "Severity affects both the violation log and the category sub-score penalty" in §3 source → reproduced as the sub-score-impact column of the added section.
- Source §8 Versioning discipline ("bumps the minor version and records the change in a short changelog appended here") → reproduced as the version-bump + changelog-entry expectation.

**Expectations satisfied:** all five (three tiers with standard impacts, overall 70 ceiling, consequence-not-effort framing + `unclassified` escape hatch, minor-version bump + dated changelog, weights untouched + no fourth tier invented).

## Eval 3 — `define-fingerprint-for-new-model-tier`

**Prompt:** "We are adding Claude Haiku 4.5 … add the canonical model tag, add a behavioural fingerprint row … Haiku is a fast non-reasoning tier; expect sub-second to ~1.5s latency and terse output with minimal preamble."

**Skill-directed behaviour:**
1. Model tag values subsection: add `claude-haiku-4.5` to the canonical list, alongside existing entries (`gpt-4.1`, `gpt-5-mini`, `claude-sonnet-4.6`, `claude-opus-4.7`).
2. Rule "adding a new model means adding a new fingerprint row" → tag and fingerprint row ship in the same version bump.
3. Layer 2 fingerprint-table row: tier = Fast non-reasoning; latency = sub-second to ~1.5s; style = terse / minimal preamble / concise structure.
4. Versioning: minor bump (1.1.0 → 1.2.0) + dated one-line changelog entry.
5. Scope guard: only the model-tag list and the fingerprint table grow; three-layer protocol structure and severity taxonomy are left intact (per Freeze-vs-Revise: this change doesn't touch either).

**Cross-check against `probe-scoring-rubric.md`:**
- §5 Model tag values: existing canonical list is exactly what the skill requires to grow, and the source shows the canonical naming convention (`provider-model-version`) Haiku's tag follows.
- §7.2 Behavioural fingerprint: existing table columns (Tier, Latency fingerprint, Style fingerprint) are exactly what the added row populates. The latency-fingerprint convention ("sub-second", "1–3 s typical", ">5 s typical") matches the Haiku row's format.
- §8 v1.1.0 changelog entry format (`1.1.0 — 2026-04-18 — added §7 Model Execution Verification …`) matches the expected v1.2.0 entry format.

**Expectations satisfied:** all five (minor bump + dated changelog, tag added alongside existing, fingerprint row with all three fields populated correctly for fast non-reasoning tier, tag-and-fingerprint shipped together, three-layer protocol and severity taxonomy untouched).

## Scope-boundary check

All three evals exercise rubric-design mechanics: category weighting, severity design, schema specification, model-verification authoring, scorecard template definition, and versioning. None require PROBE to *execute* test cases, capture streams, diff file-system state, populate a scorecard with run data, append test logs, or clean up. Those are the `run-test-plan` skill's territory and are explicitly listed in this skill's `NOT for:` clause. The scorecard template this skill defines is a shape runners fill in — this skill authors the empty template; the other skill fills it.

## Verdict

All three evals produce behaviour that is traceable to both the new `design-test-rubric` skill and the source `probe-scoring-rubric.md`. Rubric-design content was extracted faithfully; execution content was left to the parallel `run-test-plan` dispatch and is not duplicated here.
