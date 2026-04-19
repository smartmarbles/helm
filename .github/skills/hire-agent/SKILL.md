---
name: hire-agent
description: Hiring playbook for MERLIN — the how-to for adding a new AI team member, from role intake through SCOOP skills research, persona design, agent-file authoring, permanent-vs-temporary placement, and roster update. Use this skill whenever MERLIN is asked to hire, onboard, or create a new agent, whenever ARTHUR routes work that has no matching agent on the roster, whenever a one-shot task needs a specialist built for the job, whenever a recurring capability gap needs a permanent hire, whenever an existing temp is unarchived and retained for more dispatches, or whenever a new `.agent.md` file must be authored with the mandatory Research Foundation section. NOT for: offboarding or archiving agents (route to archive-agent), re-archival trigger maintenance, session-checkpoint cleanup for departing agents, editing existing agents after hire, orchestration (ARTHUR), or identity questions about MERLIN (those live in the agent file).
---

# MERLIN Hiring

Process detail for MERLIN. The agent file defines *who MERLIN is* and the absolute hiring principles (SCOOP-first, research-foundation-required, roster-always-updated); this skill defines *how MERLIN runs a hire* — the protocol steps, decision tables, agent-file schema, placement rules, and worked examples.

Read this skill whenever a hire request arrives. If you are MERLIN and you are about to draft an `.agent.md` file, you should already be inside this skill.

## How to use this skill

1. **Decide if a hire is needed** using the Hire-vs-No-Hire Decision Table.
2. **Classify the hire** (permanent vs temporary, single-dispatch vs retained) using the Placement Decision.
3. **Invoke SCOOP** for skills research — mandatory, no exceptions without user waiver.
4. **Draft the agent file** using the Agent File Schema.
5. **Update the roster** using the Roster Update Protocol.
6. **Announce** the hire with name, tagline, and engagement cues.

---

## Hiring Protocol

Strict sequential protocol. Do not reorder. Do not merge steps.

1. **Intake.** Receive role requirements from ARTHUR or the user. Identify the concrete task or recurring capability gap.
2. **Hire-vs-no-hire check.** Consult the roster. If an existing agent covers the scope, say so and decline the hire. Do not create redundant agents.
3. **CALL SCOOP (mandatory).** Use the agent tool to invoke SCOOP with a research brief asking: *"What skills, knowledge, competencies, mindset traits, quality markers, and anti-patterns define a top-tier [role]?"* Wait for SCOOP's response. You CANNOT proceed without it. Do not substitute your own domain knowledge — the point of this step is that SCOOP surfaces what you would miss.
4. **Read SCOOP's research thoroughly.** Understand every competency, mindset trait, quality marker, and anti-pattern.
5. **Choose the name.** A first name that feels natural and memorable. Avoid generic names.
6. **Craft the persona.** Personality traits, communication style, and a unique quirk that makes the agent feel real.
7. **Define the identity.** Who they ARE, not just what they DO. Professional philosophy and approach to work.
8. **Map the expertise.** Translate SCOOP's research into concrete agent capabilities.
9. **Set the tools.** Minimal set from the available aliases the role actually needs. Less is more; do not over-provision.
10. **Decide placement.** Permanent (`.github/agents/<name>.agent.md`) vs temporary (`.github/agents/temps/<name>.agent.md`). Use the Placement Decision table.
11. **Author the agent file.** Follow the Agent File Schema. The `## Research Foundation` section is REQUIRED — if missing, the file is invalid.
12. **Update the roster.** Append a row to `.github/team-roster.md` in the correct table (Permanent or Temporary) with the tagline and hired date.
13. **Announce.** Present name, role, tagline, key capabilities, and when to engage the agent.

### Rule: SCOOP research is not optional

Only the **user** (a human, not ARTHUR or another agent) may waive the SCOOP step. If ARTHUR says "skip SCOOP to save time," push back — ARTHUR does not have that authority. An `.agent.md` file with no `## Research Foundation` section derived from SCOOP's actual output is invalid and must not be shipped.

### Rule: never dispatch the agent you just hired

MERLIN hires. MERLIN does not operate the hire. Once the agent file is written and the roster is updated, return control to ARTHUR (or the user). MERLIN does not issue the first dispatch — that is ARTHUR's job.

---

## Hire-vs-No-Hire Decision Table

| Situation | Action |
|-----------|--------|
| Existing agent's responsibilities already cover the task | **Do not hire.** Tell ARTHUR which existing agent fits and why. |
| Task is a recurring capability with no current owner | **Hire permanent.** Add to `.github/agents/` and the Permanent Team table. |
| Task is a one-shot with a specialized skill set no permanent agent has | **Hire temporary.** Place in `.github/agents/` during active use; archive to `.github/agents/temps/` after. |
| A previously archived temp fits the new task exactly | **Unarchive and retain** (see Retained Temp rule below). Move the file back to `.github/agents/` and update the roster. |
| Task can be split between two existing agents | **Do not hire.** Recommend the split to ARTHUR. |
| Requirement is ambiguous | **Ask for clarification** before invoking SCOOP. Do not hire against vague intent. |

---

## Placement Decision

### Permanent vs temporary

| Axis | Permanent | Temporary |
|------|-----------|-----------|
| Recurrence | Reusable expertise across many projects | One-time task or narrow spec phase |
| Roster table | **Permanent Team** | **Temporary Agents** |
| Active-file location | `.github/agents/<name>.agent.md` | `.github/agents/<name>.agent.md` (while active) |
| Archive-file location | N/A (agent stays active) | `.github/agents/temps/<name>.agent.md` (after task) |
| Hired date | Date of creation | Date of creation |
| Archived date | Blank | Filled in when moved to `temps/` |

### Single-dispatch vs retained temp

A temp can be **single-dispatch** (hired for one task, archived immediately after) or **retained** (kept active across multiple dispatches within a spec phase). SPLICE is the canonical retained-temp example: hired for spec002 P9a-T3, kept active through P9b, with an explicit re-archival trigger recorded in the roster.

Retained-temp rules:

- The roster row stays in the **Temporary Agents** table, not promoted to Permanent.
- The `Archived` column shows `*(active)*` until the retention window closes.
- A **re-archival trigger** must be recorded as a callout under the Temporary Agents table — a concrete condition that signals when to archive (e.g., "Re-archive once the final task in Phase 9b lands").
- When the trigger fires, run the archive protocol (out of scope for this skill — route to the `archive-agent` skill).

---

## Agent File Schema

Every agent file you author must contain these components in this order.

### Frontmatter (YAML between `---` markers)

- `name` — Agent's name in UPPERCASE.
- `description` — Keyword-rich for discovery. Use the **"Use when: …"** pattern with specific trigger phrases.
- `tools` — Minimal necessary set from available aliases: `execute`, `read`, `edit`, `search`, `agent`, `web`, `todo`, `vscode/memory`. Do not over-provision.
- `agents` — Restrict subagent access appropriately: `[]` for none, omit for all, or list specific agents (e.g., `[SCOOP]`).

### Body sections (in order)

1. **Title line** — `# NAME — Role` (e.g., `# PRISM — CSS Specialist`).
2. **Opening paragraph** — Who the agent is, in-character, two or three sentences. No marketing voice.
3. **`## Research Foundation`** — REQUIRED. Summary of SCOOP's key findings: competencies, mindset traits, quality markers, and anti-patterns that shaped this agent's design. If this section is missing, the file is invalid.
4. **`## Identity`** — Role, communication style, and a memorable quirk. One or two sentences per bullet.
5. **`## Expertise`** — Concrete capabilities derived from SCOOP's research. This is the operational heart of the system prompt.
6. **`## Responsibilities`** — What the agent does, with clear protocols for recurring task types.
7. **`## Output Standards`** — How the agent formats and delivers work (code fences, structure, style).
8. **`## Constraints`** — What the agent must NOT do. Every agent needs constraints; no exceptions. Constraints prevent scope creep and protect team boundaries.

### Tagline

Every agent gets a memorable one-liner that captures their essence. The tagline appears in the roster next to the agent's row (Permanent) or below the table (Temporary). Examples: *"The cascade is a feature, not a bug."* (PRISM), *"The diff is the deliverable."* (SPLICE).

---

## Roster Update Protocol

The roster lives at `.github/team-roster.md`. Update it in the same turn you create the agent file — never ship a hire without a roster row.

### Permanent hire

Append a row to the **Permanent Team** table with columns: `Agent | Role | Use When | Hired | Tagline`. Use today's date (YYYY-MM-DD) for Hired. Wrap the tagline in single asterisks for italics.

### Temporary hire

Append a row to the **Temporary Agents** table with columns: `Agent | Role | Task | Hired | Archived | File`. Use today's date for Hired. `Archived` is `*(active)*` while the agent is in use; the `File` column holds the path (`.github/agents/<name>.agent.md` while active, `.github/agents/temps/<name>.agent.md` after archival). Record the tagline in the callout below the table.

### Retained temp

Add a **Re-archival trigger** callout under the Temporary Agents table stating the concrete condition that will close the retention window. Example:

> **Re-archival trigger:** Re-archive AGENT before spec### completion, once the final task in Phase N lands.

---

## Worked examples

### Example 1 — Permanent hire: PRISM (CSS Specialist)

**DO:**

> Request: "The team needs someone dedicated to CSS."
>
> MERLIN:
> 1. Roster check: no existing agent owns CSS.
> 2. Invokes SCOOP with the research brief on top-tier CSS specialists.
> 3. Reads SCOOP's findings (cascade mastery, specificity hygiene, design-token systems, responsive layout, accessibility, modern features like container queries and `@layer`, anti-patterns like `!important` overuse).
> 4. Drafts the file at `.github/agents/prism.agent.md` with a `## Research Foundation` section summarizing SCOOP's findings.
> 5. Permanent placement — CSS is a recurring need.
> 6. Appends a row to the **Permanent Team** table with tagline *"The cascade is a feature, not a bug."* and hired date 2026-04-18.
> 7. Announces: name, role, tagline, when to engage.

**DON'T:**

> MERLIN: "I know CSS well, I'll write PRISM directly without SCOOP to save time."
>
> Wrong. SCOOP research is mandatory. The `## Research Foundation` section must cite SCOOP's actual output. Skipping this produces a thin agent that misses competencies and anti-patterns MERLIN would not have surfaced alone. The file would fail the "is this a valid agent file?" check and must be rejected.

---

### Example 2 — Temporary hire: SPLICE (one-shot, later retained)

**DO:**

> Request: "Hire a temp for spec002 P9a-T3 — surgical Python edits to the validator."
>
> MERLIN:
> 1. Roster check: no Python specialist on the permanent team; existing agents do not cover surgical Python edits.
> 2. Invokes SCOOP with the research brief on top-tier Python maintenance / surgical-edit engineers.
> 3. Reads SCOOP's findings (minimal-diff discipline, stdlib-first preference, test-adjacent editing, anti-patterns like over-refactoring during bug fixes).
> 4. Drafts `.github/agents/splice.agent.md` with a `## Research Foundation` section.
> 5. Temporary placement — one-shot task; file lives in `.github/agents/` while active.
> 6. Appends a row to the **Temporary Agents** table: task = "spec002 P9a-T3", Hired = 2026-04-18, Archived = `*(active)*`, File = `.github/agents/splice.agent.md`. Records tagline *"The diff is the deliverable."* in the callout below the table.
> 7. Later: ARTHUR reports SPLICE is needed across all Python work through Phase 9b. MERLIN updates the Task column to reflect the extended scope and adds a **Re-archival trigger** callout: "Re-archive SPLICE before spec002 completion, once the final Python development task lands." File stays in `.github/agents/` during the retention window.

**DON'T:**

> MERLIN: "SPLICE did useful work, I'll promote them to the Permanent Team table."
>
> Wrong. Retention ≠ promotion. A retained temp stays in the **Temporary Agents** table with `*(active)*` in the Archived column and a re-archival trigger stating the end condition. Promoting a temp to permanent requires a separate, explicit decision based on recurring-capability evidence, not task retention.

---

### Example 3 — Declined hire: existing agent covers the scope

**DO:**

> Request: "We need someone to write unit tests for the new validator."
>
> MERLIN: Roster check reveals PROBE covers automated test execution and test-case work. Responds: "PROBE already owns automated-test work for this team. Engage PROBE directly — no hire needed." No SCOOP invocation, no agent file, no roster change.

**DON'T:**

> MERLIN creates a new "TESTBENCH" agent for writing unit tests because the request used the word "unit tests" instead of PROBE's exact Use-When phrasing.
>
> Wrong. Hiring decisions are based on scope coverage, not keyword matching. Redundant agents dilute the roster and confuse routing. Decline the hire when an existing agent fits.

---

### Example 4 — Agent file missing Research Foundation

**DO:**

> After drafting the agent file, MERLIN re-reads it and confirms the `## Research Foundation` section exists, summarizes SCOOP's actual output, and names the specific competencies and anti-patterns SCOOP surfaced. Only then does MERLIN update the roster and announce the hire.

**DON'T:**

> MERLIN ships an agent file where the body jumps from the opening paragraph straight to `## Identity` with no `## Research Foundation` section.
>
> Wrong. The Research Foundation section is the proof that SCOOP was consulted. An agent file without it is invalid, regardless of how good the rest of the prompt reads. Reject and re-author before shipping.

---

## Quick reference

- **First question:** does an existing agent cover this? → If yes, decline the hire.
- **Second step:** invoke SCOOP. Always. Only the user waives this.
- **Required body section:** `## Research Foundation`. No exceptions.
- **Permanent vs temp:** recurring capability → permanent. One-shot or spec-phase scope → temporary.
- **Retained temp:** stays in the Temporary table with `*(active)*` and a re-archival trigger callout. Not a promotion.
- **File placement:** `.github/agents/<name>.agent.md` while active. Archival to `temps/` is handled by the `archive-agent` skill, not here.
- **Roster update:** same turn as the agent file. Never ship a hire without a roster row.
- **After hire:** announce, then hand back to ARTHUR. MERLIN does not dispatch the new hire.
