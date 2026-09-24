# MERLIN Hiring

Process detail for MERLIN. The agent file defines *who MERLIN is* and the absolute hiring principles (SCOOP-first, research-foundation-required, roster-always-updated); this skill defines *how MERLIN runs a hire* — the protocol steps, decision tables, agent-file schema, placement rules, and worked examples.

Read this skill whenever a hire request arrives. If you are MERLIN and you are about to draft an agent's authored source, you must already be inside this skill.

## How to use this skill

1. **Decide if a hire is needed** using the Hire-vs-No-Hire Decision Table.
2. **Classify the hire** (permanent vs temporary, single-dispatch vs retained) using the Placement Decision.
3. **Invoke SCOOP** for skills research — mandatory, no exceptions without user waiver.
4. **Draft the authored source and the per-host wrappers** using the Agent File Schema.
5. **Update the roster** using the Roster Update Protocol.
6. **Announce** the hire with name, tagline, and engagement cues.

---

## Hiring Protocol

Strict sequential protocol. Do not reorder. Do not merge steps.

1. **Intake.** Receive role requirements from ARTHUR or the user. Identify the concrete task or recurring capability gap.
2. **Hire-vs-no-hire check.** Consult the roster. If an existing agent covers the scope, say so and decline the hire. Do not create redundant agents.
3. **CALL SCOOP (mandatory).** Use `invoke-subagent` to invoke SCOOP with a research brief asking: *"What skills, knowledge, competencies, mindset traits, quality markers, and anti-patterns define a top-tier [role]?"* Wait for SCOOP's response. You CANNOT proceed without it. Do not substitute your own domain knowledge — the point of this step is that SCOOP surfaces what you would miss.
4. **Read SCOOP's research thoroughly.** Understand every competency, mindset trait, quality marker, and anti-pattern.
5. **Choose the name.** A first name that feels natural and memorable. Avoid generic names.
6. **Craft the persona.** Personality traits, communication style, and a unique quirk that makes the agent feel real.
7. **Define the identity.** Who they ARE, not just what they DO. Professional philosophy and approach to work.
8. **Map the expertise.** Translate SCOOP's research into concrete agent capabilities.
9. **Decide the capability grant.** Identify the minimal set of capability-vocabulary verbs (`read-file`, `edit-file`, `find-files`, `search-content`, `run-command`, `fetch-url`, `invoke-subagent`, `access-working-store`, `ask-user`, `track-tasks`) the role actually needs. Less is more; do not over-provision. This decision is translated into each host's concrete tool identifiers only when authoring that host's wrapper frontmatter (step 11b) — never hand-maintained as a tool list in the authored source itself.

   **Working-store access decision:** Default: permanent agents receive `access-working-store` in their capability grant; temp agents do not. Record the decision and rationale when deviating from the default. The criterion is cross-dispatch continuity need, not output type.

10. **Decide placement.** Permanent vs temporary using the Placement Decision table. This decision does not change where the authored source lives — `.helm/agents/<name>.md` is the same path either way — it only changes which wrapper archive-path variant applies later (a temp's VS Code wrapper eventually moves to `.github/agents/temps/<name>.agent.md`; a permanent's does not).
11. **Author the agent's files.** Two parts, both required, per the Agent File Schema:
    - **(a)** Author the host-agnostic source at `.helm/agents/<name>.md` — the one file a human edits. The `## Research Foundation` section is REQUIRED — if missing, the file is invalid.
    - **(b)** Author one thin wrapper per in-scope host discovery path (VS Code Copilot, Claude Code, Devin Desktop, Cursor), each carrying that host's native frontmatter plus an instruction pointer back to the authored source — never independent behavioural content.
12. **Update the roster.** Append a row to `.github/team-roster.md` in the correct table (Permanent or Temporary) with the tagline and hired date.
13. **Announce.** Present name, role, tagline, key capabilities, and when to engage the agent.
14. **Draft SKILL.md.** When the new agent has a skill to create, read `.helm/playbooks/skill-creator/skill-creator.md` as structural reference. Draft the skill's `SKILL.md` with proper frontmatter (`name`, `description` with trigger language and "NOT for:" clause), body content.

    **Skill size limit (≤500 lines):** The `SKILL.md` body must be under 500 lines. This is a hard limit — skills load in full on every trigger, and oversized bodies degrade instruction-following reliability on weaker models. If the content would exceed 500 lines, apply this split strategy:
    - **Keep in SKILL.md:** procedural steps the agent must execute (the workflow), constraints, decision tables, and output format rules
    - **Move to `references/`:** worked examples, lookup tables, scoring templates, appendix material — reference with a link and one-line description in the skill body
    The skill body is the *executor*; `references/` files are the *lookup library*. The agent follows the skill and reads references only when needed.
15. **Run validator.** Run `python .github/scripts/validate_skill.py <skill-dir>` using `run-command`. Fix all errors. Report any warnings. A skill is not complete until the validator passes with zero errors.
16. **Minimum-viable eval.** Ensure `evals/evals.json` exists with at least 1 test case (3+ recommended). Deliver the eval alongside the agent file.

### Validation Contract

> Post-creation validation with `validate_skill.py` is mandatory. A skill task is not complete until the validator exits with zero errors. Skipping this step is a workflow violation regardless of time pressure or task complexity. ARTHUR must confirm validation was executed and passed before accepting the task as complete.

### Rule: SCOOP research is not optional

Only the **user** (a human, not ARTHUR or another agent) may waive the SCOOP step. If ARTHUR says "skip SCOOP to save time," push back — ARTHUR does not have that authority. An authored source with no `## Research Foundation` section derived from SCOOP's actual output is invalid and must not be shipped.

### Rule: never dispatch the agent you just hired

MERLIN hires. MERLIN does not operate the hire. Once the agent's files are written and the roster is updated, return control to ARTHUR (or the user). MERLIN does not issue the first dispatch — that is ARTHUR's job.

---

## Hire-vs-No-Hire Decision Table

| Situation | Action |
|-----------|--------|
| Existing agent's responsibilities already cover the task | **Do not hire.** Tell ARTHUR which existing agent fits and why. |
| Task is a recurring capability with no current owner | **Hire permanent.** Author `.helm/agents/<name>.md` plus the per-host wrapper set (see Agent File Schema), and add to the Permanent Team table. |
| Task is a one-shot with a specialized skill set no permanent agent has | **Hire temporary.** Author `.helm/agents/<name>.md` plus the per-host wrapper set, each wrapper at that host's active discovery path; the wrapper set is archived (handled by the `archive-agent` skill) after. |
| A previously archived temp fits the new task exactly | **Unarchive and retain** (see Retained Temp rule below). Restore the wrapper set to each host's active discovery path and update the roster. |
| Task can be split between two existing agents | **Do not hire.** Recommend the split to ARTHUR. |
| Requirement is ambiguous | **Ask for clarification** before invoking SCOOP. Do not hire against vague intent. |

---

## Placement Decision

### Permanent vs temporary

| Axis | Permanent | Temporary |
|------|-----------|-----------|
| Recurrence | Reusable expertise across many projects | One-time task or narrow spec phase |
| Roster table | **Permanent Team** | **Temporary Agents** |
| Authored-source location | `.helm/agents/<name>.md` — same path either way, never moves | `.helm/agents/<name>.md` — same path either way, never moves |
| Wrapper active-file locations | `.github/agents/<name>.agent.md`, `.claude/agents/<name>.md`, `.devin/agents/<name>.md`, `.cursor/agents/<name>.md` | Same four paths, while active |
| Wrapper archive-file location | N/A (agent stays active) | VS Code wrapper moves to `.github/agents/temps/<name>.agent.md` after task (handled by the `archive-agent` skill — out of scope here); the other three hosts' wrappers are addressed by that same skill |
| Hired date | Date of creation | Date of creation |

> **Discovery rule:** Each in-scope host discovers agent wrappers only at that host's own discovery path — e.g. VS Code Copilot scans `.github/agents/` directly, with no subdirectory recursion. New temps must be created with an active-location wrapper on every in-scope host while active. Archival of the wrapper set is handled by the `archive-agent` skill, not here.

### Single-dispatch vs retained temp

A temp can be **single-dispatch** (hired for one task, archived immediately after) or **retained** (kept active across multiple dispatches within a spec phase). SPLICE is the canonical retained-temp example: hired for spec002 P9a-T3, kept active through P9b, with an explicit re-archival trigger recorded in the roster.

Retained-temp rules:

- The roster row stays in the **Temporary Agents** table, not promoted to Permanent.
- A **re-archival trigger** must be recorded as a callout under the Temporary Agents table — a concrete condition that signals when to archive (e.g., "Re-archive once the final task in Phase 9b lands").
- When the trigger fires, run the archive protocol (out of scope for this skill — route to the `archive-agent` skill).

---

## Agent File Schema

Every hired agent (permanent or temporary) is represented by **one authored source plus one thin wrapper per in-scope host discovery path** — never a single per-host file. The authored source is the only file a human edits for that agent's identity and rules; wrappers carry no independent behavioural content of their own. `.helm/agents/arthur.md` (and its four wrapper files) is the reference pattern — read it before authoring a new agent.

### (a) Authored source — `.helm/agents/<name>.md`

#### Frontmatter (YAML between `---` markers)

- `name` — Agent's name in UPPERCASE.
- `description` — Keyword-rich for discovery. Use the **"Use when: …"** pattern with specific trigger phrases.

No `tools` or subagent-restriction field belongs in the authored source's frontmatter — a capability grant is a per-host wrapper concern (part (b) below), never hand-maintained here.

> **Skill-first check:** Before authoring each body section, ask: *"Does this describe a repeatable process?"* If yes, it belongs in a companion skill or playbook, not the agent file. Body content describes who the agent is and what it does; procedural how-to lives in a `SKILL.md` under `.github/skills/` or a playbook under `.helm/playbooks/`.

> **Line limit:** Role-specific body content must stay ≤ 100 lines (frontmatter excluded). If the body would exceed this, move procedural or lookup content to a companion skill, playbook, or `references/` file and add a one-line link in the agent file.

#### Body sections (in order)

1. **Title line** — `# NAME — Role` (e.g., `# PRISM — CSS Specialist`).
2. **Opening paragraph** — Who the agent is, in-character, two or three sentences. No marketing voice.
3. **`## Research Foundation`** — REQUIRED. Summary of SCOOP's key findings: competencies, mindset traits, quality markers, and anti-patterns that shaped this agent's design. If this section is missing, the file is invalid.
4. **`## Identity`** — Role, communication style, and a memorable quirk. One or two sentences per bullet.
5. **`## Expertise`** — Concrete capabilities derived from SCOOP's research. This is the operational heart of the system prompt.
6. **`## Responsibilities`** — What the agent does, with clear protocols for recurring task types.
7. **`## Output Standards`** — How the agent formats and delivers work (code fences, structure, style).
8. **`## Constraints`** — What the agent must NOT do. Every agent needs constraints; no exceptions. Constraints prevent scope creep and protect team boundaries.

### (b) Per-host wrappers — one per in-scope host discovery path

For every in-scope host, author a thin wrapper at that host's discovery path:

| Host | Wrapper path (active) |
|---|---|
| VS Code Copilot | `.github/agents/<name>.agent.md` |
| Claude Code | `.claude/agents/<name>.md` |
| Devin Desktop | `.devin/agents/<name>.md` |
| Cursor | `.cursor/agents/<name>.md` |

Each wrapper carries:

- That host's own native frontmatter — its real, role-scoped capability grant (a Devin `allowed-tools` list, a Cursor `model`/`readonly`/`is_background` set, a VS Code `tools` list, a Claude Code `tools` list, plus any subagent-restriction field that host supports). Scope every grant to the agent's actual role — never default to a host's full available capability ceiling. `name` and `description` are copied verbatim from the authored source; that duplication is the only hand-visible content a wrapper repeats.
- A pointer instructing the host to read the authored source in full before acting, reusing the Mandatory-Read Template from `AGENTS.md` verbatim in structure, targeting `.helm/agents/<name>.md`.
- No independent behavioural content — a wrapper that restates or extends the authored source's rules is wrong; it must point, not duplicate.

Example — `.github/agents/arthur.agent.md`:

```
---
name: "ARTHUR"
description: "AI Team Orchestrator. Use when: ..."
tools: [agent, read, todo, vscode/memory]
---

> **MANDATORY READ — `.helm/agents/arthur.md`**
>
> Before performing this task, you MUST read `.helm/agents/arthur.md` in full. This is not optional. Do not improvise from memory. If the file cannot be loaded, STOP and report the failure — do not proceed without it. Failure to load is a protocol violation.
```

The same shape repeats for `.claude/agents/arthur.md` (Claude-native `tools` identifiers), `.devin/agents/arthur.md` (`allowed-tools`), and `.cursor/agents/arthur.md` (`model` / `readonly` / `is_background`) — only the frontmatter vocabulary changes per host; the pointer body is identical across all four.

### Tagline

Every agent gets a memorable one-liner that captures their essence. The tagline appears in the `Tagline` column of the roster row — identical format for both permanent and temporary agents. Examples: *"The cascade is a feature, not a bug."* (PRISM), *"The diff is the deliverable."* (SPLICE).

---

## Roster Update Protocol

The roster lives at `.github/team-roster.md`. Update it in the same turn you create the agent's files — never ship a hire without a roster row.

### Permanent hire

Append a row to the **Permanent Team** table with columns: `Agent | Role | Use When | Hired | Tagline`. Use today's date (YYYY-MM-DD) for Hired. Wrap the tagline in single asterisks for italics.

### Temporary hire

Append a row to the **Temporary Agents** table using the same format as the **Permanent Team** table: `Agent | Role | Use When | Hired | Tagline`. Use today's date for Hired. Place the tagline directly in the `Tagline` column — do not add a callout below the table.

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
> 4. Drafts the authored source at `.helm/agents/prism.md` with a `## Research Foundation` section summarizing SCOOP's findings, then authors the four per-host wrappers (`.github/agents/prism.agent.md`, `.claude/agents/prism.md`, `.devin/agents/prism.md`, `.cursor/agents/prism.md`), each pointing at the authored source with role-scoped, host-native frontmatter.
> 5. Permanent placement — CSS is a recurring need.
> 6. Appends a row to the **Permanent Team** table with tagline *"The cascade is a feature, not a bug."* and hired date 2026-04-18.
> 7. Announces: name, role, tagline, when to engage.

**DON'T:**

> MERLIN: "I know CSS well, I'll write PRISM directly without SCOOP to save time."
>
> Wrong. SCOOP research is mandatory. The `## Research Foundation` section must cite SCOOP's actual output. Skipping this produces a thin agent that misses competencies and anti-patterns MERLIN would not have surfaced alone. The file would fail the "is this a valid authored source?" check and must be rejected.

---

### Example 2 — Temporary hire: SPLICE (one-shot, later retained)

**DO:**

> Request: "Hire a temp for spec002 P9a-T3 — surgical Python edits to the validator."
>
> MERLIN:
> 1. Roster check: no Python specialist on the permanent team; existing agents do not cover surgical Python edits.
> 2. Invokes SCOOP with the research brief on top-tier Python maintenance / surgical-edit engineers.
> 3. Reads SCOOP's findings (minimal-diff discipline, stdlib-first preference, test-adjacent editing, anti-patterns like over-refactoring during bug fixes).
> 4. Drafts the authored source at `.helm/agents/splice.md` with a `## Research Foundation` section, then authors the four per-host wrappers (`.github/agents/splice.agent.md`, `.claude/agents/splice.md`, `.devin/agents/splice.md`, `.cursor/agents/splice.md`), each pointing at the authored source.
> 5. Temporary placement — one-shot task; the wrapper set lives at each host's active discovery path while active.
> 6. Appends a row to the **Temporary Agents** table using the permanent format: `Use When` = "spec002 P9a-T3 surgical Python edits", Hired = 2026-04-18, Tagline = *"The diff is the deliverable."* — identical structure to a permanent row.
> 7. Later: ARTHUR reports SPLICE is needed across all Python work through Phase 9b. MERLIN updates the `Use When` column to reflect the extended scope and adds a **Re-archival trigger** callout: "Re-archive SPLICE before spec002 completion, once the final Python development task lands."

**DON'T:**

> MERLIN: "SPLICE did useful work, I'll promote them to the Permanent Team table."
>
> Wrong. Retention ≠ promotion. A retained temp stays in the **Temporary Agents** table (same row format as permanent) with a re-archival trigger callout stating the end condition. Promoting a temp to permanent requires a separate, explicit decision based on recurring-capability evidence, not task retention.

---

### Example 3 — Declined hire: existing agent covers the scope

**DO:**

> Request: "We need someone to write unit tests for the new validator."
>
> MERLIN: Roster check reveals the test runner covers automated test execution and test-case work. Responds: "The test runner already owns automated-test work for this team. Engage the test runner directly — no hire needed." No SCOOP invocation, no agent files, no roster change.

**DON'T:**

> MERLIN creates a new "TESTBENCH" agent for writing unit tests because the request used the word "unit tests" instead of the test runner's exact Use-When phrasing.
>
> Wrong. Hiring decisions are based on scope coverage, not keyword matching. Redundant agents dilute the roster and confuse routing. Decline the hire when an existing agent fits.

---

### Example 4 — Agent file missing Research Foundation

**DO:**

> After drafting the authored source, MERLIN re-reads it and confirms the `## Research Foundation` section exists, summarizes SCOOP's actual output, and names the specific competencies and anti-patterns SCOOP surfaced. Only then does MERLIN author the per-host wrappers, update the roster, and announce the hire.

**DON'T:**

> MERLIN ships an authored source where the body jumps from the opening paragraph straight to `## Identity` with no `## Research Foundation` section.
>
> Wrong. The Research Foundation section is the proof that SCOOP was consulted. An authored source without it is invalid, regardless of how good the rest of the prompt reads. Reject and re-author before shipping the wrappers.

---

## Quick reference

- **First question:** does an existing agent cover this? → If yes, decline the hire.
- **Second step:** invoke SCOOP. Always. Only the user waives this.
- **Required body section:** `## Research Foundation`. No exceptions.
- **Permanent vs temp:** recurring capability → permanent. One-shot or spec-phase scope → temporary.
- **Retained temp:** stays in the Temporary table (same format as permanent) with a re-archival trigger callout below the table. Not a promotion.
- **File placement:** authored source at `.helm/agents/<name>.md` (never moves) plus one thin wrapper per in-scope host at that host's active discovery path. Archival of the wrapper set is handled by the `archive-agent` skill, not here.
- **Roster update:** same turn as the agent's files. Never ship a hire without a roster row.
- **After hire:** announce, then hand back to ARTHUR. MERLIN does not dispatch the new hire.
