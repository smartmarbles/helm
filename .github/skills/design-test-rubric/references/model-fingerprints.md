# Model Fingerprints and Flagging Rules

## Behavioural Fingerprint Table

| Model | Tier | Latency fingerprint | Style fingerprint |
|-------|------|---------------------|-------------------|
| **Sonnet 4.6** (`claude-sonnet-4.6`) | Reasoning | Response latency to complex prompts **>5 s typical**; visible reasoning-model pause before first token; distinctive reasoning-trace preamble if the client exposes it. | Measured, enumerated; frequently uses explicit step markers. |
| **GPT-5 mini** (`gpt-5-mini`) | Mid-tier non-reasoning | Latency **1–3 s typical**; no reasoning pause. | Shorter verbosity than GPT-4.1; terser preamble; less "certainly!" hedging. |
| **GPT-4.1** (`gpt-4.1`) | Fallback | **Sub-second** responses on short prompts; no reasoning pause. | Characteristic verbose preamble ("Certainly! Here's…", "Of course!"); high-affect scaffolding. |

## Flagging and Retry Rules

| Signal pattern | Action |
|----------------|--------|
| Layer 3 returns mismatch | **Abort batch.** Do not dispatch further test cases. Reschedule only after the user re-confirms. |
| Layer 1 and Layer 2 disagree with the requested model | Flag the individual run. Repeat the probe/run once; if disagreement persists, mark inconclusive and **exclude from category averages**. |
| Layer 2 verdict = inconclusive only (signal too weak) | Document as a note in the `## Verification` section. **Do not flag; do not exclude.** |
| Layer 1 pass + Layer 2 match + Layer 3 confirmed | Proceed normally; record all three in the `## Verification` section. |
