# Worked Examples

## Example 1 — Weighting a new rubric

**DO:**

> User: "Design a rubric for testing delegation discipline against GPT-4.1."
>
> PROBE: observes that GPT-4.1's dominant failure mode is orchestrators writing output directly (delegation) and forbidden tool calls firing despite prose bans (tool restriction). Allocates Delegation = 25, Tool restriction = 20 (45% combined on the two dominant failure modes), then spreads the remaining 55% across six process-quality categories at ~10% each, with Memory usage at 8 and Workflow hygiene at 7. Writes a one-sentence rationale on every row. Totals verified to 100.

**DON'T:**

> PROBE: "Eight categories, 12.5% each. Clean and fair."
>
> Wrong. Even weighting ignores the observed failure pattern. A rubric whose weights don't reflect the target model's real error profile will score a broken agent as mid-tier and hide the regressions that matter.

---

## Example 2 — Severity assignment

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

## Example 3 — Behavioural fingerprint for a new model

**DO:**

> User: "We're adding GPT-5 to the supported set. Add it to the rubric."
>
> PROBE: bumps rubric version to 1.2.0. Adds `gpt-5` to the canonical model-tag list. Adds a fingerprint row: tier = reasoning; latency fingerprint = "2–4 s typical on complex prompts; brief pause but shorter than Sonnet 4.6"; style fingerprint = "measured, enumerated, less preamble than GPT-4.1, more structure than GPT-5-mini". Adds a one-line changelog entry: "1.2.0 — added `gpt-5` canonical tag and fingerprint row".

**DON'T:**

> PROBE: "Added the tag. The fingerprint row can wait until someone runs a batch on it."
>
> Wrong. A model tag without a fingerprint row has no Layer-2 signal — verification protocol silently degrades. Tag and fingerprint ship together or not at all.

---

## Example 4 — Inconclusive verification

**DO:**

> A batch consists of short refusal-check prompts that return in under a second on every supported model. Layer 2 verdict = `inconclusive` with a note: "prompts too short to discriminate tier; latency signal not diagnostic". Layer 1 pass + Layer 3 confirmed, so the batch proceeds; the `## Verification` section documents the inconclusive fingerprint as a known limitation of this test set.

**DON'T:**

> PROBE: "Layer 2 was inconclusive, so I'm flagging every run in the batch and excluding them from category averages."
>
> Wrong. Inconclusive is not mismatch. Flagging on an inconclusive-only signal discards valid data; the correct action is to document and proceed.
