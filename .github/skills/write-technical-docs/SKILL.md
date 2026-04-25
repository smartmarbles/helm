---
name: write-technical-docs
description: Documentation-authoring playbook for QUILL — how to turn an approved design, schema, codebase, or research packet into developer-facing written artifacts (READMEs, API references, tutorials, developer guides, comparison docs, migration guides, quickstarts). Use this skill whenever QUILL is asked to write documentation, author a README, draft an API reference, produce a tutorial or quickstart, write a developer guide, compare libraries in prose, author a migration guide from version N to N+1, or turn SCOOP research or a schema into reader-facing docs. NOT for: primary research (use SCOOP), architectural decisions (use SAGE — QUILL documents decisions, does not make them), implementing features or writing production code, or test-case authoring and execution (PROBE).
---

# QUILL Documentation Authoring

Process detail for QUILL. The agent file defines *who QUILL is* and the absolute principles (radical empathy for the confused reader, verification obsession, no marketing voice). This skill defines *how QUILL writes* — the doc-type decisions, the plan-draft-review loop, the structural conventions, the code-sample discipline, and the review pass.

Read this skill whenever a task brief asks for any developer-facing written artifact. If you are QUILL and you are about to draft anything, you should already be inside this skill.

## How to use this skill

1. **Classify the doc type** using the [Doc-Type Decision Table](references/doc-type-table.md).
2. **Identify the audience** — evaluator, implementer, or troubleshooter — and state it in the opening.
3. **Plan the structure first** (outline before prose).
4. **Draft code before prose.** Every section leads with a runnable snippet; the prose explains it.
5. **Run the review pass** before declaring complete.
6. **Refine** until the Confused Developer Test passes.

---

→ [Boundaries](references/boundaries.md) — role-ownership table and refusal scripts for writing vs. researching vs. deciding

→ [Doc-Type Decision Table](references/doc-type-table.md) — lookup table mapping doc type to use case, governing question, and required sections, plus the "Which am I writing?" decision heuristic

---

## Audience calibration

Before drafting, answer these three questions in writing (internally or in the session checkpoint):

1. **Who is the reader?** Evaluator (deciding whether to adopt), implementer (already committed, building now), or troubleshooter (something broke)?
2. **What do they already know?** Language proficiency, familiarity with the domain, familiarity with the specific library or framework.
3. **What are they trying to accomplish?** The single question that brought them to this page.

State the audience in the document's opening sentence or an explicit "Who this is for" callout. Every paragraph that follows earns its place by answering a question this reader is likely to have.

→ [Writing Standards](references/writing-standards.md) — terminology gating rules and mixed-audience layering patterns

---

## Writing protocol

Every doc authoring task follows these five steps. Do not skip.

### 1. Plan

Before writing any prose:

- State audience, doc type, and governing question in one or two sentences.
- Outline the section headings. For large docs (>500 lines likely), outline sections, save outline to `/memories/session/`, and plan to produce linked section files rather than one monolith (see Large Document Protocol below).
- Identify which code samples are needed. For each, note: the concept it demonstrates (one per sample), the language, the library version, and whether it can be verified.
- If any required code sample cannot be verified, flag it now — either request access to verify, or plan to wrap the sample in a `> **Version Note:** ...` callout acknowledging the limitation.

### 2. Draft code first

For each section, write the code sample before the surrounding prose.

- Write imports first. Show the full `import` or `#include` or `use` line.
- Pin the version in a line-1 comment when relevant: `// typescript 5.4, @my/lib 2.1.0`.
- Keep the sample minimal and runnable: one concept per sample, no extraneous setup, no `// ...` placeholders in critical paths.
- Use well-typed idiomatic code for the language (TypeScript with explicit types at function boundaries, Python with type hints for non-trivial signatures, etc.).
- If the output or behaviour matters, show expected output as a comment or a separate fenced block below the code.

Only then write the prose around the sample. Prose explains what the code does and why; it does not introduce concepts that the code does not demonstrate.

### 3. Draft prose

- Short paragraphs: 3–4 sentences maximum. One idea per paragraph.
- Active voice, present tense, second person ("you") for instructions.
- Front-load the TL;DR. The first paragraph of each section tells the reader what the section will give them. The last paragraph tells them what they now have.
- Headings are question-oriented or task-oriented: "How do I authenticate?", "Setting up the database", "Comparing `useEffect` and `watchEffect`". Avoid noun-only headings like "Authentication" unless the section is pure reference.
- Use tables for structured comparisons. Always include prose commentary *after* a large table — tables inform, prose interprets. A table with no surrounding prose forces the reader to do the synthesis themselves.
- Use callouts for warnings, notes, and version flags:
  - `> **Note:** ...` — side information the reader should notice.
  - `> **Warning:** ...` — behaviour the reader will get wrong if they ignore it.
  - `> **Version Note:** This applies to library X v2.1.0 and may change in future releases.` — claims likely to drift.

### 4. Review pass

Before declaring complete, run this checklist. Every item. Every time.

- **Accuracy** — did I verify every code sample against the actual API at the stated version? If not, is it explicitly flagged?
- **Structure** — does every section's first paragraph tell the reader what they'll get? Does every section end with a synthesis or handoff to the next section?
- **Terminology** — did I define every specialized term on first use? Did I use each term consistently thereafter?
- **Headings** — are they question- or task-oriented? Does each answer or frame a reader question?
- **Code samples** — complete imports shown? Version pinned? Runnable? One concept per sample?
- **Callouts** — warnings where the reader can get it wrong? Version notes on claims likely to drift?
- **Comparisons** — every comparison section ends with a verdict (2–3 sentence synthesis)? No false balance (trivial and major points given equal space)?
- **Marketing voice** — any "blazing fast", "incredibly easy", "powerful", "seamlessly" without evidence? Strip them.
- **Links** — relative paths between project docs? Anchor links for within-document navigation? No broken links?
- **Typos and grammar** — read the whole thing top to bottom one more time.
- **Confused Developer Test** — imagine a frustrated developer at 11 PM trying to ship. Does every paragraph help them or slow them down? Sections that slow them down get rewritten.

### 5. Refine

Rewrite anything that fails the review pass. Rewrite is not "polish" — it is substantive. Common rewrites:

- A concept introduced before the code that demonstrates it → flip the order.
- A table with no commentary after it → add a 2–3 sentence synthesis.
- A comparison section with no verdict → add one.
- An unverified code sample without a version-note callout → add one, or verify and remove the note.
- Jargon used before definition → move the definition above first use, or remove the jargon.

---

→ [Structural Conventions](references/structural-conventions.md) — headings, code blocks, tables, callouts, feature gap matrix, and front-loaded summary patterns

---

## Large Document Protocol

For any doc likely to exceed ~500 lines (full API references, multi-chapter guides, large comparison docs):

1. **Outline first.** Save the full section outline to `/memories/session/` before writing any content.
2. **Section per file.** Produce each section as a separate file (`setup.md`, `api-reference.md`, `examples.md`) rather than one monolithic file.
3. **Checkpoint between sections.** Update `/memories/session/` after each completed section with: target folder, full outline, filenames of completed sections, key decisions (terminology choices, structural decisions, scope changes).
4. **Index last.** Once all sections are done, write `index.md` that introduces the document set, describes each file's scope, and links to every section.
5. **Prefer linked files.** A well-structured set of linked files is more scannable, easier to maintain, and more resilient to interruption than a single large file.

---

→ [Output Standards](references/output-standards.md) — format, file placement, length, version pinning, full imports, and unstable API flagging rules

---

→ [Worked Examples](references/worked-examples.md) — four DO/DON'T pairs: concept-before-code ordering, comparison verdicts, unverified code samples, and SCOOP research transformation

---

→ [Quick Reference](references/quick-reference.md) — nine-bullet summary lookup for common decision points


