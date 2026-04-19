---
name: create-spec
description: Specification authoring playbook for SAGE — the how-to for turning a user request into a written feature specification (Overview, User Scenarios, Requirements, Success Criteria, Edge Cases) that an implementer can plan against without further clarification. Use this skill whenever SAGE is asked to produce a spec, whenever ARTHUR routes work down the full path ("create a spec", "let's spec this out", "full path"), whenever a feature needs scoping before planning, whenever open questions and acceptance criteria must be captured before implementation, or whenever a request is too ambiguous to plan directly and needs an intent-capture pass first. NOT for: producing implementation plans or phased task breakdowns (use the create-plan skill), research-only requests that return findings in-conversation (route to SCOOP), code or documentation deliverables (SAGE does not implement), or identity/persona questions about SAGE (those live in the agent file).
---

# Create a Spec

Process detail for SAGE when the deliverable is a feature specification. The agent file defines *who SAGE is* and the non-negotiable principles; this skill defines *how SAGE turns a request into a spec* — intent capture, structure, open questions, and checkpoint handoff.

Read this skill whenever SAGE is about to write a `spec.md`. If you are SAGE and the task is "create a spec" or you are on the full path before any plan exists, you should already be inside this skill. Planning — phases, dependencies, file assignments, parallelization — is a separate deliverable covered by the `create-plan` skill. Do not blend the two.

## How to use this skill

1. **Confirm the path** — a spec is a full-path artifact. If ARTHUR routed this as research or standard, stop and ask before producing one.
2. **Capture intent** before structure. Restate the request in your own words and list what you believe the user is asking for.
3. **Surface open questions** early — do not bury them in the doc.
4. **Draft the spec** using the required structure below.
5. **Checkpoint** after each major section.
6. **Write the artifact to disk** with `create_file`. Never return the spec content as response text.
7. **Hand off** at the Spec Checkpoint — report the file path and a brief summary, then wait for human approval.

---

## When a spec is the right output

| Situation | Spec needed? |
|-----------|--------------|
| User explicitly said "create a spec" / "spec this out" / "full path" | **Yes** |
| ARTHUR routed the task as full path | **Yes** |
| Net-new feature, migration, or rewrite | **Yes** |
| Request is ambiguous and needs scope before planning can begin | **Yes** |
| Research-only ("investigate", "compare", "look into") | **No** — route to SCOOP |
| Multi-file change with clear intent, no new surface area | **No** — go straight to the `create-plan` skill |
| One-file fix, bug patch, obvious edit | **No** — no spec, no plan |

### Rule: explicit path requests are binding

If the user or ARTHUR named the full path, write the spec even if the feature seems small. Do not downgrade. Do not skip directly to a plan to "save a turn".

---

## Spec Authoring Protocol

Five steps. Do not reorder. Do not merge steps.

1. **Research first (via SCOOP).** Before writing a single line of the spec, delegate technical research to SCOOP through the agent tool: API capabilities, codebase patterns, library behaviour, known gotchas. You read SCOOP's findings; you do not read the codebase yourself. SCOOP is the research expert — use the subagent.
2. **Verify externalities.** If the spec depends on external libraries, APIs, or platform behaviour, use web search to confirm current documentation. Training knowledge is in the past; the docs are in the present.
3. **Capture intent.** Write one paragraph in your own words stating what is being built and why. If restating reveals ambiguity, list it in Open Questions before continuing.
4. **Outline before drafting.** Sketch the Overview, P1/P2/P3 scenarios, and the FR list as bullet points first. This surfaces gaps before you commit them to prose.
5. **Draft the full spec** using the required structure. Every section is filled in — no placeholder text, no "TBD" left behind.

### Rule: intent first, structure second

A spec written before intent is captured will confidently document the wrong feature. If after restating the request you cannot tell what "done" looks like, stop and ask the user — or put the ambiguity in Open Questions and flag it at the Spec Checkpoint.

---

## Required Spec Structure

Use `.github/templates/spec-template.md` as the starting structure. Every spec MUST include these sections, in order:

### Overview
What is being built and why. Two to three sentences. No implementation detail.

### User Scenarios
Prioritized user stories:
- **P1** — primary scenario, always present, with ≥2 acceptance-criteria checkboxes.
- **P2** — secondary scenario, present when scope includes more than a single happy path.
- **P3** — optional; add only when scope genuinely warrants it.

Each scenario uses the **"As a [user], I want [goal], so that [benefit]"** form with acceptance criteria as checkboxes.

### Requirements
Functional requirements in an ID/Description/Priority/Scenario table. IDs follow **FR-001** format, numbered sequentially. Priority is **Must / Should / Could**. Every FR maps to at least one scenario.

Add a **Key Entities** table when the feature introduces domain objects with non-trivial attributes.

### Success Criteria
Measurable outcomes that define "done". IDs follow **SC-001** format. Each criterion states whether it is measurable (yes/no) — prefer yes.

### Edge Cases
Bullet list of what happens when inputs, state, or environment deviate from the happy path. This section is non-negotiable — omitting it means the spec is incomplete.

### Non-Functional Requirements
Optional. Add performance, accessibility, security, or compliance requirements only when scope warrants them.

### Open Questions
Uncertainties or decisions that need user input before planning can begin. Never hide them. If you have none, say "None" explicitly.

---

## Spec Checkpoint — Handoff Expectations

After the spec is written, ARTHUR runs the Spec Checkpoint before any plan is generated. SAGE's responsibility is to make that checkpoint possible:

1. **Write the file to disk** with `create_file`. Path: `artifacts/spec###-short-name/spec.md`. Never return the spec content as response text.
2. **Report back** to ARTHUR in this exact shape:
   - The spec folder path
   - The file(s) written
   - A 1–2 sentence summary of what the spec covers
   - The count of Open Questions (so ARTHUR knows to surface them)
3. **Stop.** Do not start a plan. Do not volunteer a plan. The user owns the checkpoint decision.

### Rule: narration is not delivery

A spec that exists only in your response text did not get written. Every spec deliverable must include an actual `create_file` tool call. If you catch yourself describing spec contents in prose without a file-write tool call alongside it, stop and emit the tool call.

---

## Artifact Location

Specs live in numbered spec folders under `artifacts/`:

1. **ARTHUR assigns the folder name.** If ARTHUR gave you one (e.g., `artifacts/spec004-fix-payment-timeout/`), use it.
2. **If no folder was specified**, scan `artifacts/` for the highest existing `spec###-*` folder, increment the number, and use a generic short name (`spec###-unnamed`) flagged for ARTHUR to rename.
3. **If no spec folders exist at all**, use `artifacts/spec001-unnamed/` (or the provided short name).
4. **`create_file` creates missing parent directories automatically.** Do not run a separate mkdir step. Do not ask the user for permission to create the folder — just write.
5. **Filename is always `spec.md`.**

---

## Session Resumption

Specs often span multiple sections; checkpoint as you go.

- **Before starting:** check `/memories/session/` (or `.agent-memory/session/` in memory-less mode) for a prior checkpoint on this spec. If found, resume from the next incomplete section rather than starting over.
- **While working:** after completing each major section (Overview, each scenario block, FR table, Success Criteria, Edge Cases, Open Questions), write a checkpoint recording: target spec folder, current stage, completed sections, and any key decisions or open questions captured so far.
- **After completing:** clear the checkpoint.

See `AGENTS.md` for the full Session Resumption Protocol.

---

## Worked examples

### Example 1 — Intent capture before drafting

**DO:**

> User: "I want a way for premium users to export their data."
>
> SAGE (via SCOOP research on existing export/auth patterns, then):
>
> > **Intent:** Premium-tier users can trigger an export of their account data and receive it via a download or email delivery. Scope appears to be: which data is included, how the user triggers it, how it is delivered, and rate-limiting for abuse.
>
> Drafts P1 = in-app trigger → download, adds Open Questions: "Which data classes are in scope? Email delivery or in-app only? Retention of generated exports?"

**DON'T:**

> SAGE writes a full spec assuming CSV-only, in-app download, 24-hour retention — none of which the user specified. The spec is internally consistent but documents a feature the user did not ask for. Open Questions section is empty.
>
> Wrong. Capture intent and surface ambiguity before committing to structure. An authoritative-sounding spec built on unverified assumptions is worse than a spec with visible open questions.

---

### Example 2 — Spec Checkpoint handoff

**DO:**

> SAGE writes `artifacts/spec007-data-export/spec.md` with `create_file`, then reports:
>
> > Spec written to `artifacts/spec007-data-export/spec.md`. Covers premium-user data export: P1 in-app CSV download, P2 email delivery, 6 FRs, 3 success criteria. **3 Open Questions** need user input before planning: data classes in scope, retention policy, rate limits.
>
> Stops. Does not begin a plan.

**DON'T:**

> SAGE: "Here is the spec content: [dumps 200 lines of markdown]. I'll now start on the plan."
>
> Wrong on two counts. First, the spec was not written to disk — narration is not delivery. Second, the Spec Checkpoint is a hard stop; plans do not start until the user approves the spec. No exceptions.

---

### Example 3 — Wrong path

**DO:**

> User: "Compare Redis vs Memcached for our session store."
>
> SAGE recognizes this as research, not a spec. Responds: "This looks like a research request, not a full-path feature spec. I'd recommend routing to SCOOP for a comparison. If you want a spec for a specific session-store migration after the research lands, I can produce one then."

**DON'T:**

> SAGE writes a feature spec titled "Session Store Selection" with scenarios and FRs. The artifact looks impressive but the user wanted findings, not a product spec.
>
> Wrong. A spec is a full-path artifact for building something. Research questions do not produce specs.

---

## Quick reference

- **Is a spec the right output?** → Check the decision table. Full path or explicit request only.
- **Research before drafting?** → Always. SCOOP first; never read the codebase yourself.
- **Intent captured?** → Restate in your own words before structure.
- **Open Questions surfaced?** → Explicit section, never hidden. "None" is a valid answer; silence is not.
- **Edge Cases filled in?** → Non-negotiable.
- **Written to disk?** → `create_file` always. Narration is not delivery.
- **Checkpoint handoff?** → Report path, files, summary, Open-Questions count. Then stop.
