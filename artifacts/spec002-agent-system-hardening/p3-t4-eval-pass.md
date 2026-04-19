# P3-T4 Eval-Pass Walkthrough — `write-technical-docs` skill

Logical walkthrough verifying each eval prompt, when handled by QUILL loading the `write-technical-docs` skill, produces behaviour that matches the skill's guidance and traces to `quill.agent.md` — confined to documentation authoring (research lives with SCOOP, architectural decisions with SAGE).

## Eval 1 — `write-readme-for-new-package`

**Prompt:** README for `@widget/client` v2.1.0 (TypeScript, `WidgetClient` class, three methods, Node 20+), audience is both evaluators and implementers.

**Skill-directed behaviour:**
1. Doc-Type Decision Table → **README** (first developer contact, mixed evaluator+implementer audience). Required sections: one-line summary, Why/When, Prerequisites, Install, Quickstart (runnable), Links to deeper docs, License/Contributing link.
2. Audience calibration → mixed audience rule fires: first 60s serves evaluators (what/why/when), Quickstart serves implementers, troubleshooters are NOT served in main flow (scoped to separate section or link).
3. Writing protocol step 1 (plan): audience + doc type stated in opening. Step 2 (draft code first): Quickstart sample contains full `import` line and line-1 version-pin comment (`// typescript 5.4, @widget/client 2.1.0`). Step 3 (prose): question/task-oriented headings, short paragraphs.
4. Output standards: full imports, version pinned, expected output shown after sample.
5. Review pass: no marketing voice ("blazing fast", "incredibly easy", "powerful" stripped). Only the three documented methods appear — no fabrication.

**Cross-check against `quill.agent.md`:**
- Identity: "a feature without good docs is an incomplete feature" — README is the feature's first doc.
- Writing Protocol step 1 (identify audience) + step 2 (write the code first) are invoked directly.
- Output Standards: full imports, version pinning, callouts — all reproduced.
- Constraint: "no marketing language" — enforced in review-pass item and eval expectation #4.

**Expectations satisfied:** all five (opening + audience statement; Prerequisites/Install/Quickstart with version-pinned sample and expected output; only documented methods; question-oriented headings + no marketing voice; deeper-docs + license/contributing + troubleshooting not in main flow).

## Eval 2 — `author-api-reference-from-schema`

**Prompt:** Reference entry for `WidgetClient.widgets.create` given signature, returns, errors, side effects; use a template consistent across all methods.

**Skill-directed behaviour:**
1. Doc-Type Decision Table → **API reference**. Governing question: "what does this identifier do, what does it take, what does it return?" Required template: signature, parameters (with types), return value, side effects, errors/exceptions, minimal example, See also.
2. Structural conventions: every identifier in backticks (inherited from agent file's "Every identifier in backticks" rule). Optional parameters explicitly marked. Enum values enumerated.
3. Writing protocol step 2 (code first): example is minimal runnable TypeScript with full `import` line and line-1 version-pin comment. One concept per sample (create a widget) — no extraneous setup.
4. Review pass: no fabricated behaviour. The schema specifies signature + errors + one side effect. QUILL does NOT invent batch mode, idempotency, or retry semantics.
5. Terminology gating: `ValidationError`, `RateLimitError`, `NetworkError` used exactly as schema names them — no renaming.

**Cross-check against `quill.agent.md`:**
- Expertise → API References: "Parameter types, return values, side effects, edge cases. Consistent template per entry. Every identifier in backticks." Reproduced verbatim in both skill guidance and eval #1/#2/#3 expectations.
- Output Standards: "Full imports — Show complete `import` statements in code samples" + "target a specific package or library version" — enforced.
- Constraint: "Do NOT write code samples you haven't verified against the actual API" — the schema IS the verified source; the skill tells QUILL to transcribe it faithfully and not invent extensions.

**Expectations satisfied:** all five (per-entry template with fixed section order; parameters + optional + enum; all three errors + side-effect endpoint; minimal versioned example; no fabrication + no marketing voice).

## Eval 3 — `write-migration-guide-v1-to-v2`

**Prompt:** Migration guide from `@widget/client` v1.x → v2.1.0 with four named breaking changes; audience = implementers with working v1 code.

**Skill-directed behaviour:**
1. Doc-Type Decision Table → **Migration guide**. Required sections: version pinning (from X.Y.Z to A.B.C), breaking-change summary table, concept mapping, step-by-step transition path, gotchas, rollback note.
2. Audience calibration: implementer with working code; state audience in opening. Doc is NOT a tutorial (reader is not learning from zero) and NOT a comparison (no choice being made).
3. Structural conventions: feature-change table with v1 vs v2 columns; side-by-side code panels for constructor change and method rename, both fenced TypeScript with full imports and line-1 version-pin comments; `> **Warning:** ...` callout for the error-handling change (exactly the shape defined in Callouts).
4. Writing protocol step 4 (review pass): no fabricated breaking changes beyond the four listed. No marketing voice ("seamless migration", "effortless upgrade" stripped).
5. Structural conventions → rollback note present; rollback instructions use version pinning and Node downgrade — concrete, actionable.

**Cross-check against `quill.agent.md`:**
- Expertise → Migration Guides: "Concept mapping between frameworks, gotchas, and step-by-step transition paths." Reproduced as the required-sections row in the Doc-Type Decision Table.
- Output Standards: "Pin version numbers explicitly in document headers and code comments." — enforced in eval expectations #1 and #2.
- Constraint: "Do NOT use marketing language" — enforced in expectation #5. Constraint: don't fabricate — enforced in expectation #5.

**Expectations satisfied:** all five (version-pin header + audience + change summary table with all four changes; side-by-side v1/v2 code panels with imports and version pins; numbered transition path covering all four changes; `> **Warning:**` callout for error-handling gotcha + rollback note; no fabricated changes + no marketing voice).

## Scope-boundary check

All three evals exercise documentation authoring:
- Doc-type classification (README / API ref / migration guide)
- Audience statement and calibration
- Code-first drafting with version pinning
- Review-pass disciplines (no marketing voice, no fabrication, consistent terminology, verdict where needed)
- Structural conventions (tables, side-by-side panels, callouts, headings)

None require QUILL to:
- Research library capabilities from scratch (that is SCOOP's territory; the schemas and breaking-change lists are provided in each prompt — the skill tells QUILL to transcribe faithfully, not to investigate)
- Decide which approach or library is better (that is SAGE's territory; no eval asks for a recommendation between options)
- Implement features or write production code (QUILL never builds)
- Author or run test cases (that is PROBE's territory)

Those boundaries are explicitly called out in the skill's `NOT for:` clause and enforced by the "Boundaries: writing vs researching vs deciding" section.

## Verdict

All three evals produce behaviour traceable to both the new `write-technical-docs` skill and the source `quill.agent.md`. Documentation-authoring content was extracted faithfully (doc-type decision table, writing protocol, structural conventions, review pass, large-document protocol, worked examples). Identity, Persona, and absolute principles (verification obsession, no marketing voice, radical empathy) remain in the agent file; the skill references them as inviolable but does not restate the persona.
