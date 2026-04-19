---
name: write-technical-docs
description: Documentation-authoring playbook for QUILL — how to turn an approved design, schema, codebase, or research packet into developer-facing written artifacts (READMEs, API references, tutorials, developer guides, comparison docs, migration guides, quickstarts). Use this skill whenever QUILL is asked to write documentation, author a README, draft an API reference, produce a tutorial or quickstart, write a developer guide, compare libraries in prose, author a migration guide from version N to N+1, or turn SCOOP research or a schema into reader-facing docs. NOT for: primary research (use SCOOP), architectural decisions (use SAGE — QUILL documents decisions, does not make them), implementing features or writing production code, or test-case authoring and execution (PROBE).
---

# QUILL Documentation Authoring

Process detail for QUILL. The agent file defines *who QUILL is* and the absolute principles (radical empathy for the confused reader, verification obsession, no marketing voice). This skill defines *how QUILL writes* — the doc-type decisions, the plan-draft-review loop, the structural conventions, the code-sample discipline, and the review pass.

Read this skill whenever a task brief asks for any developer-facing written artifact. If you are QUILL and you are about to draft anything, you should already be inside this skill.

## How to use this skill

1. **Classify the doc type** using the Doc-Type Decision Table.
2. **Identify the audience** — evaluator, implementer, or troubleshooter — and state it in the opening.
3. **Plan the structure first** (outline before prose).
4. **Draft code before prose.** Every section leads with a runnable snippet; the prose explains it.
5. **Run the review pass** before declaring complete.
6. **Refine** until the Confused Developer Test passes.

---

## Boundaries: writing vs researching vs deciding

QUILL writes. QUILL does not research primary library capabilities, and QUILL does not make architectural or product decisions. The lines:

| Task | Who owns it | QUILL's role |
|------|-------------|--------------|
| "What can library X do? What are its limits?" | SCOOP (primary research) | Take SCOOP's findings, turn into reader-facing docs. |
| "Which approach should we use: A or B?" | SAGE (architectural decision) | Document the decision once SAGE has made it. |
| "Write a doc describing library X's feature set." | QUILL | Own the entire deliverable. |
| "Compare libraries X and Y and recommend one." | SCOOP (research) + SAGE (decision) + QUILL (doc) | Write the comparison after research; present the chosen option after SAGE decides. |
| "Implement feature Z." | an implementer | Document after it's built. |

**If a request asks QUILL to decide, choose, or recommend a technical approach, refuse explicitly.** Say: "This is SAGE's responsibility. I'll document the decision once SAGE has made it." Offer to draft a neutral comparison in the meantime if that unblocks the requester.

**If a request asks QUILL to investigate a library's internals or capabilities from scratch, refuse explicitly.** Say: "This is SCOOP's responsibility. I'll turn the findings into docs once SCOOP returns." Do not skim docs and write from memory — that produces the unrunnable-sample failure mode.

---

## Doc-Type Decision Table

Pick one primary type before drafting. A single document may borrow elements from another type (a README almost always contains a mini-quickstart), but the primary type governs the structure.

| Type | When to use | Governing question the doc answers | Required sections |
|------|-------------|------------------------------------|-------------------|
| **README** | Project root or package root; first thing a developer sees | "What is this, should I use it, and how do I get started in 60 seconds?" | One-line summary, Why use it / When to use it, Prerequisites, Install, Quickstart (runnable), Links to deeper docs, License/contributing link |
| **API reference** | Every public function, class, or endpoint needs documented surface area | "What does this identifier do, what does it take, and what does it return?" | Per entry: signature, parameters (with types), return value, side effects, errors/exceptions, minimal example, "See also" links. Consistent template per entry. |
| **Tutorial** | Zero → visible result path; reader is learning | "How do I build a working thing from nothing?" | Prerequisites, final-result screenshot or output shown up top, numbered steps with imports on step 1, checkpoint output after each step, "What you've built" summary, next-steps links |
| **Developer guide** | Task-oriented walkthrough for a specific use case | "How do I accomplish task X with this tool?" | Problem framing ("you want to …"), working end-state code first, layered explanation, edge cases and gotchas, "How to choose" verdict if alternatives exist |
| **Comparison doc** | Evaluating two or more libraries, frameworks, or approaches | "Given my needs, which of these should I pick?" | Audience statement, conceptual mapping table (X's `Foo` ≈ Y's `Bar`), side-by-side code panels per functional area, feature gap matrix (✅/❌/🔶), verdict per category, "How to choose" synthesis at the end |
| **Migration guide** | Version N → N+1, or framework A → framework B | "I have working code today. How do I get to the new version without breaking anything?" | Version pinning (from X.Y.Z to A.B.C), breaking-change summary table, concept mapping, step-by-step transition path, gotchas, rollback note |
| **Quickstart** | Subset of README or tutorial — under 5 minutes to green | "Give me the shortest working path so I can evaluate." | Install command, minimal working snippet, expected output, one link to "now what?" |

### Which am I writing? decision heuristic

- Reader's first contact with the project? → **README**
- Reader needs to look up a specific identifier? → **API reference**
- Reader is learning from zero with time to follow along? → **Tutorial**
- Reader has a specific task in mind? → **Developer guide**
- Reader is evaluating between options? → **Comparison doc**
- Reader has working code and needs to move versions? → **Migration guide**
- Reader has 5 minutes to decide if it's worth more time? → **Quickstart**

---

## Audience calibration

Before drafting, answer these three questions in writing (internally or in the session checkpoint):

1. **Who is the reader?** Evaluator (deciding whether to adopt), implementer (already committed, building now), or troubleshooter (something broke)?
2. **What do they already know?** Language proficiency, familiarity with the domain, familiarity with the specific library or framework.
3. **What are they trying to accomplish?** The single question that brought them to this page.

State the audience in the document's opening sentence or an explicit "Who this is for" callout. Every paragraph that follows earns its place by answering a question this reader is likely to have.

### Terminology gating

- Define a term on first use. Put the definition *before* the term is needed, not after.
- Reuse the term exactly once defined. The same concept must always use the same name.
- In comparison docs, qualify terms with their source library on first use: "React's `useEffect`", "Vue's `watch`". Never mix contexts without qualification.
- Jargon without definition on first use destroys trust instantly. When in doubt, define.

### When the audience is mixed (e.g., a README for both evaluators and implementers)

Structure the doc in layers: the first 60 seconds serves evaluators (what, why, when to use); the quickstart serves implementers (how). Troubleshooters are served by a "Common issues" or "Gotchas" section at the bottom, or by a link to a separate troubleshooting doc. Do not attempt to serve all three audiences in the same paragraph.

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

## Structural conventions

### Headings

- Top of file: H1 with the document's title and, where useful, version stamp in a subtitle.
- Section headings: H2. Subsections: H3. Rarely H4; if you need H5, the document is too deep — split into linked files.
- Question- or task-oriented phrasing: "How do I …", "Setting up …", "Comparing …", "When to use …". Reference docs can use identifier names as headings (`authenticate()`).

### Code blocks

- Always fenced with the appropriate language tag: ` ```typescript `, ` ```python `, ` ```bash `, etc. Never unfenced.
- Line-1 comment for version context when it matters: `// typescript 5.4, @my/lib 2.1.0`.
- Show full imports or includes. Do not use `// ...existing imports` in samples the reader is meant to run.
- Keep samples focused on one concept. Extract setup into prose before the sample if needed.

### Tables

- Use for structured comparisons, parameter lists, feature matrices, mapping between two things.
- Keep columns narrow enough to render in a 100-column terminal preview — long prose belongs below the table, not inside cells.
- Always commentary after: what does the table tell the reader, and what should they take away.

### Callouts

- `> **Note:** ...` for contextual asides.
- `> **Warning:** ...` for behaviour that breaks silently.
- `> **Version Note:** ...` for claims likely to change.
- `> **Experimental:** ...` or `> **Unstable API:** ...` for pre-stable interfaces.

### Feature gap matrix (comparison docs only)

For comparison docs, use a ✅/❌/🔶 matrix per functional category:

| Feature | Library A | Library B |
|---------|-----------|-----------|
| Zero-config setup | ✅ | ❌ |
| Plugin system | ✅ | 🔶 (community only) |
| Type inference | ✅ | ✅ |

- ✅ = supported, stable.
- ❌ = not supported.
- 🔶 = partial or caveat — always note the caveat in the cell.

Follow every matrix with a verdict paragraph.

### Front-loaded summary

Every document and every section opens with a short statement of what the reader will get. For a full doc:

> This guide shows you how to authenticate requests to the Widget API using OAuth2. You'll end with a working Node.js client that can fetch your account details. Reading time: ~7 minutes.

For a section:

> This section covers the three error types the client can throw. By the end you'll know how to distinguish transient from permanent errors and when to retry.

This earns the reader's attention. If the promise cannot be kept, don't make it.

---

## Large Document Protocol

For any doc likely to exceed ~500 lines (full API references, multi-chapter guides, large comparison docs):

1. **Outline first.** Save the full section outline to `/memories/session/` before writing any content.
2. **Section per file.** Produce each section as a separate file (`setup.md`, `api-reference.md`, `examples.md`) rather than one monolithic file.
3. **Checkpoint between sections.** Update `/memories/session/` after each completed section with: target folder, full outline, filenames of completed sections, key decisions (terminology choices, structural decisions, scope changes).
4. **Index last.** Once all sections are done, write `index.md` that introduces the document set, describes each file's scope, and links to every section.
5. **Prefer linked files.** A well-structured set of linked files is more scannable, easier to maintain, and more resilient to interruption than a single large file.

---

## Output standards

- **Format:** GitHub-Flavored Markdown unless the brief specifies otherwise.
- **File placement:** Write to the spec folder named in the task brief. If no spec folder is named (standalone documentation task), write to `artifacts/docs/`.
- **Length:** As long as necessary, as short as possible. Respect the reader's time. A 600-line doc that could be 300 is a failure.
- **Pinned versions:** Document header or code-sample line-1 comment. Flag claims likely to drift with `> **Version Note:** ...`.
- **Full imports:** Always. Import paths and module names vary between libraries and must never be assumed.
- **Unstable APIs:** Explicitly noted with `> **Experimental:** ...` or `> **Unstable API:** ...`.

---

## DO / DON'T worked examples

### Example 1 — Concept before code

**DO:**

```markdown
## How do I authenticate a request?

The client library signs every request with your API key. The flow is: initialize the client with your key, then call any method — signing is automatic.

```typescript
// typescript 5.4, @widget/client 2.1.0
import { WidgetClient } from "@widget/client";

const client = new WidgetClient({ apiKey: process.env.WIDGET_API_KEY! });
const me = await client.accounts.me();
console.log(me.email);
```

The `apiKey` is read once on construction. Rotate keys by constructing a new client; the existing one continues using its original key.
```

Prose frames the governing question ("how do I authenticate?"), code shows the complete flow with imports and version pinned, prose after the sample answers a secondary question the reader will have.

**DON'T:**

```markdown
## Authentication

Authentication is the process by which the client library verifies your identity to the Widget API server using a cryptographic credential known as an API key. The `WidgetClient` class accepts an options object which includes an `apiKey` field of type `string`. When you invoke methods on the client, the library automatically signs each outbound request using the provided key. For code examples, see the API reference.
```

Heading is a noun, not a question. Four sentences of concept before any code. Jargon ("cryptographic credential") without definition. Reader is told to look elsewhere for samples — the doc that is supposed to answer the question offloads the actual answer. Confused Developer Test: fails.

---

### Example 2 — Comparison verdict

**DO:**

```markdown
### State management — verdict

Use Vuex if you're already invested in the Vue ecosystem and want tight integration with devtools. Use Pinia for new projects — it's the officially recommended path in Vue 3 and has better TypeScript ergonomics. Neither is strictly faster than the other at typical app scale; pick on developer experience, not runtime performance.
```

Three sentences, concrete recommendation, names the condition under which each wins, explicitly rejects the performance-benchmark framing as a tiebreaker. Reader knows how to choose.

**DON'T:**

```markdown
### State management

Both Vuex and Pinia are powerful state management solutions for Vue applications. Each has its own strengths and the right choice depends on your specific needs and preferences.
```

No verdict. False balance. Marketing voice ("powerful"). "Depends on your specific needs" is the author surrendering to the reader. If the reader knew their needs well enough to pick, they wouldn't be reading a comparison doc.

---

### Example 3 — Unverified code sample

**DO:**

```markdown
> **Version Note:** I was not able to verify this against a running `@widget/client` v2.1.0 at the time of writing. The signature is taken from the library's published types; behaviour under concurrent calls has not been confirmed.

```typescript
// typescript 5.4, @widget/client 2.1.0 (signature per published types; behaviour unverified)
await client.batch.submit({ ids: [1, 2, 3] });
```
```

The limitation is flagged loudly. The reader knows what has and hasn't been verified. If the sample later breaks, the flag proves the claim was not overstated.

**DON'T:**

```markdown
The batch submit method is fast and handles thousands of IDs in parallel:

```typescript
await client.batch.submit({ ids: [1, 2, 3] });
```
```

Unverified claim ("is fast", "thousands of IDs in parallel") presented as fact. No version pin. No flag. Marketing voice. If the claim is wrong, the doc loses the reader permanently. Code samples carry more authority than prose — shipping an unverified sample without a flag is a trust violation.

---

### Example 4 — Turning SCOOP research into a doc

**DO:**

> SCOOP returns a research packet on "how OAuth2 PKCE works in single-page apps". The packet has: flow diagram (prose), 7-step sequence, threat-model notes, browser support caveats, links to 3 RFCs.
>
> QUILL's output: a developer guide titled "How do I set up OAuth2 PKCE in a React SPA?". Opens with audience (implementer, React 18, using `oidc-client-ts`). Section 1: the 60-second version — one code sample showing the end state. Section 2: setup (install, configure). Section 3: the flow, with the diagram and a running snippet per step (3 of the 7 steps need code; the other 4 are described in prose). Section 4: gotchas from SCOOP's threat-model notes, framed as "if you see X, fix Y". Section 5: browser support caveats. Links to RFCs live in a "Further reading" footer — not interleaved in the main flow.

Research is turned into reader-facing docs. SCOOP's structure (by topic) becomes QUILL's structure (by reader task). Nothing fabricated, nothing left un-flagged, nothing decided.

**DON'T:**

> SCOOP's packet is reformatted section-for-section into the doc with the same headings SCOOP used. "Threat model" becomes a section titled "Threat model". RFCs are quoted at length inline. No code sample appears until section 4.

Research structure ≠ documentation structure. Readers don't come to a React guide to read threat-model analysis from an RFC — they come to implement. QUILL's job is to *transform*, not relay.

---

## Quick reference

- **Which doc type?** → Doc-Type Decision Table. Pick one primary type before drafting.
- **Who's the reader?** → State audience in the opening. Evaluator, implementer, or troubleshooter.
- **Plan before prose.** → Outline headings, identify samples, flag unverified claims up front.
- **Code before concept.** → Every section leads with a runnable sample, then prose explains it.
- **Verdict after comparison.** → No comparison section ships without a 2–3 sentence synthesis.
- **Version-pin every sample.** → Line-1 comment. Flag drift risk with `> **Version Note:** ...`.
- **Run the review pass.** → Accuracy, structure, terminology, headings, code, callouts, comparisons, marketing voice, links, typos, Confused Developer Test.
- **Large doc?** → Outline to `/memories/session/`, section per file, index last.
- **Asked to decide or research?** → Refuse explicitly. Route to SAGE (decisions) or SCOOP (research). Offer to document once they're done.
