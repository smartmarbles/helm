# Writing Standards

## Terminology gating

- Define a term on first use. Put the definition *before* the term is needed, not after.
- Reuse the term exactly once defined. The same concept must always use the same name.
- In comparison docs, qualify terms with their source library on first use: "React's `useEffect`", "Vue's `watch`". Never mix contexts without qualification.
- Jargon without definition on first use destroys trust instantly. When in doubt, define.

## When the audience is mixed (e.g., a README for both evaluators and implementers)

Structure the doc in layers: the first 60 seconds serves evaluators (what, why, when to use); the quickstart serves implementers (how). Troubleshooters are served by a "Common issues" or "Gotchas" section at the bottom, or by a link to a separate troubleshooting doc. Do not attempt to serve all three audiences in the same paragraph.
