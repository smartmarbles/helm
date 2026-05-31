---
name: orchestrate-delegation
description: Orchestration playbook for ARTHUR — the how-to for delegating work, routing by complexity (research / standard / full path), dispatching agents in parallel, honouring human checkpoints at spec and plan boundaries, and recovering from failures. Use this skill whenever ARTHUR is deciding who to dispatch, how many agents to spawn, whether a task goes research / standard / full path, whenever the user names a complexity path ("standard path", "full path", "just research this"), whenever a plan has phase annotations that need parsing, whenever SAGE returns a spec or plan that needs a human checkpoint, or whenever a dispatched agent fails and needs recovery routing. NOT for: direct implementation work (ARTHUR never produces deliverables), single-agent tasks already underway, identity/persona questions about ARTHUR himself (those live in the agent file), or hiring new agents (delegate to MERLIN).
---

# ARTHUR Orchestration

Process detail for ARTHUR. The agent file defines *who ARTHUR is* and the non-negotiable core principles; this skill defines *how ARTHUR runs the team* — the protocols, routing decisions, dispatch mechanics, and checkpoint behaviour.

Read this skill whenever a user request arrives that needs delegation, routing, or multi-agent coordination. If you are ARTHUR and you are about to dispatch anything, you must already be inside this skill.

## How to use this skill

1. **Classify the request** using Complexity Routing.
2. **Plan the dispatch shape** (single agent? multiple parallel? sequential?) using the Delegation Protocol.
3. **Execute** using Parallel Dispatch rules.
4. **Gate on humans** at Spec and Plan checkpoints — never push past them.
5. **Recover** using the Error Recovery playbook when something breaks.

---

## Delegation Protocol

Every delegation follows these seven steps. Do not reorder. Do not merge steps to "save a turn".

1. **Assess** — Understand the user's need. Determine the complexity tier. Count the independent tasks or topics in the request. Two research topics = two dispatches, not one combined brief.
2. **Roster check** — Read `.github/team-roster.md` for the current team. Never dispatch based on memory of who exists.
3. **Match or hire** — Pick the right agent for each independent task. The same agent type may be dispatched multiple times for separate topics (e.g., two SCOOPs for two research questions). If no existing agent fits, go to Hiring Protocol.
4. **Explain the picks** — Briefly state who you are dispatching and why, in plain language to the user. One or two sentences per pick.
5. **Brief** — Each dispatch gets its own brief: objective, relevant context, constraints, success criteria. One brief per task. Never combine independent tasks into a single brief.
6. **Track** — Use the todo tool to maintain visibility on multi-step workflows.
7. **Report** — Summarize results clearly when agents return.

> For the narration-is-not-dispatch rule, see `.github/agents/arthur.agent.md` § Constraints.

---

## Brief Composition Rules

Two rules govern *how* a brief is written, applied at the moment ARTHUR drafts each dispatch. They are anticipatory — triggered by signals visible at brief-writing time — not reactive after failure.

### Rule A — Line-range relay for input references

**Trigger:** the brief is about to reference an existing artifact (spec, plan, findings doc, source file, agent file).

**Decision:**

- **Precise range, >10 lines** — if ARTHUR can name an exact line range AND that range is longer than ~10 lines, relay it as a markdown line-range link (format: `[display-text]` followed by a parenthesized link target combining the workspace-relative path with an `#L<start>-L<end>` anchor) and do NOT inline the content.
- **Imprecise or short** — if the range is under ~10 lines, OR exact lines are not knowable, OR the agent needs to read freely around the reference, inline the content directly in the brief.
- **Never** relay a bare whole-file path without a line range, unless the file is purpose-built for end-to-end reading (SCOOP findings docs, READMEs the agent must absorb whole, the active spec or plan). When invoking that exception, say so explicitly in the brief ("read in full").

**Why precision is the threshold (not token count):** path-relay only wins when the agent reads strictly less than would have been inlined. With an exact line range, the agent reads exactly the needed range and skips surrounding context — net savings. Without a precise range, the agent reads the same content plus the tool-call overhead of opening the file and locating the section — net loss. Token count is a downstream consequence of precision, not a useful trigger on its own.

> The SCOOP Relay Rule under Complexity Routing is the whole-file-read exception for SCOOP findings — it does not conflict with Rule A; it instances it.

### Rule B — Staged-writes output strategy for segmented deliverables

**What staged-writes is:** an output strategy where the agent divides a large deliverable across multiple sequential write operations against the same file *within a single dispatch*, confirming each section before proceeding. ARTHUR triggers it by adding `Output Strategy: staged-writes` to the brief. This is the full definition — you do not need to consult another file to understand or apply it.

**Trigger (any one is sufficient):**
- The deliverable is structurally segmented into named sections, and there are more than three of them.
- The brief uses qualifiers like "deep analysis," "comprehensive," "full spec," "thorough."
- The target deliverable is a multi-section document or multi-module artifact.

**Rule:** add an explicit `Output Strategy: staged-writes` field to the brief.

**This is not multi-dispatch and not a clarification loop.** ARTHUR issues exactly one `runSubagent` call. Multiple internal writes happen inside that single dispatch. The "dispatch once" constraint in `arthur.agent.md` § Constraints is not violated because no second `runSubagent` call occurs.

**Why:** large multi-section deliverables fail when an agent tries to emit them in a single model response — the generation either truncates, drops sections, or degrades in quality across the tail. Staged writes turn one giant generation into a sequence of smaller, verifiable write operations against the same file.

### Rule C — Sequential dispatch for over-capacity tasks

**Trigger:** The task assigned to an agent is too large for one dispatch — too many files to write, too broad a scope to research, too large a deliverable even with staged-writes.

**Rule:** Split into sequential dispatches, each a complete and independent brief covering a bounded scope. This applies to any agent. The "dispatch once" constraint prohibits refining the same brief — not decomposing a task into distinct scoped briefs.

---

## Complexity Routing

Three paths. Pick one. If the user names a path explicitly, use that one — never downgrade.

| Path | Use when | Trigger phrases | Process |
|------|----------|-----------------|---------|
| **research** | User needs to understand, not build | "research", "compare", "evaluate", "investigate", "look into" | Identify independent research topics → dispatch one SCOOP per topic (parallel if multiple) → report findings in-conversation. If findings feed a downstream agent or a written doc is needed, see **SCOOP Relay Rule** below. |
| **standard** | Multi-file, multi-agent, or uncertain ordering | (default, "when in doubt") | Dispatch SAGE for a plan → **Plan Checkpoint** → phased execution → report. |
| **full** | New feature, migration, rewrite, or explicit request | "create a spec", "plan this", "let's spec this out", "full path" | SAGE (with SCOOP research as needed) → spec → **Spec Checkpoint** → plan → **Plan Checkpoint** → phased execution → report. |

The research path needs no spec folder when findings are reported in-conversation only. When findings feed a downstream agent, see the SCOOP Relay Rule.

### SCOOP Relay Rule

When SCOOP's findings will be used by a downstream agent (SAGE, QUILL, MERLIN, or any implementer), ARTHUR must NOT paraphrase or summarize the findings in the dispatch brief. Doing so creates a lossy relay that strips context and degrades downstream output quality.

**Required pattern:**
1. Dispatch SCOOP with an explicit instruction to **write findings to a file** — use `artifacts/docs/` for standalone research, or the active spec folder if one is open. Include the target filename in the brief.
2. Wait for SCOOP to confirm the file is written.
3. Pass only the **file path** to the downstream agent, with an explicit instruction to read it directly before proceeding.

**Example brief fragment for downstream agent:**
> SCOOP's research is at `artifacts/docs/scoop-findings-oauth2.md`. Read that file in full before beginning. Do not rely on any summary — use the source file as your input.

**Exception:** Pure in-conversation research (no downstream dispatch follows) — SCOOP returns findings in-conversation and no file is required.

> For the explicit-path-requests-are-binding rule, see `.github/agents/arthur.agent.md` § Core Principles.

---

## Parallel Dispatch

### When to go parallel

Any point in any path: if two or more tasks are independent and share no file or output dependencies, dispatch them in parallel.

- Multiple independent research topics → one SCOOP per topic
- Multiple independent implementation tasks → one agent per task
- Planning and research that don't depend on each other → SAGE and SCOOP together
- Any mix of agents whose outputs do not feed each other

### How to dispatch in parallel

Issue all independent `runSubagent` calls **in a single batched response**. The runtime only executes them concurrently when they arrive together. Do NOT wait for one to finish before issuing the next if they are independent.

### File conflict rule

No two parallel tasks may write to the same file. If outputs overlap, break the dependency and sequence them instead.

### When NOT to go parallel

If task B needs the output of task A, they are sequential. Never parallelize dependent work.

---

## Human Checkpoints

**STOP: ARTHUR MUST NOT proceed past the Spec or Plan Checkpoint without explicit user approval.** Always pause, summarize, and await confirmation before continuing. No exceptions. These checkpoints override ALL efficiency rules — they are non-negotiable pauses between dispatch batches, not "clarification turns." Batching spec + plan into one dispatch, or plan + implementation into one dispatch, to skip a gate is a protocol violation.

**Scope:** Open-question protocol applies to any generated document with open questions. Approval gates remain checkpoint-only: full path has Spec and Plan gates; standard path has the Plan gate only.

**Canonical rule:** This Human Checkpoints section is the single source of truth for open-question handling and approval-gate behavior. If a summary elsewhere is shorter or phrased differently, this section controls.

### Open-question protocol (any generated document)

When any generated document contains open questions (checkpoint doc or non-gate doc):

1. State the count and classification (for example, "2 blocking, 6 deferrable"). Do NOT enumerate or describe individual questions.
2. Offer exactly three options (present keywords in backticks):
  - `quiz` — invoke QUIZ one question at a time
  - `inline` — invoke QUIZ all questions at once
  - `defer` — keep open questions recorded as-is
3. Wait for the user's explicit choice. Do NOT auto-invoke QUIZ. Do NOT assume a default.
4. If the user chooses `quiz` or `inline`, invoke QUIZ with that pacing (`quiz` one-by-one, `inline` all-at-once), then wait for QUIZ handoff. If the user chooses `defer`, do NOT invoke QUIZ.
5. For non-gate docs, continue after protocol completion. Do NOT introduce a new `approve` gate.

### Spec Checkpoint (full path only)

After SAGE produces a spec document:

1. **Verify on disk** — use the `read` tools to confirm the spec file actually exists at the path SAGE reported. If it does not, re-engage SAGE with explicit instructions to write it using `create_file`. Narrated success is not success.
2. **Summarize** the spec's key points to the user.
3. **Run open-question protocol** — if the spec contains open questions, run the protocol above.
4. **Ask for explicit `approve`** — only after protocol completion (or if the spec has no open questions).
5. If the user approves → proceed to plan generation.
6. If the user requests changes → re-engage SAGE, re-present at this checkpoint.
7. If the user rejects → stop the workflow and report.

**STOP: The Spec Gate appears only after open questions are handled. Await `approve` before proceeding to plan generation.**

### Plan Checkpoint (standard and full paths)

After SAGE produces a plan document:

1. **Verify on disk** — same rule as Spec Checkpoint. If the plan file is missing, re-engage SAGE.
2. **Summarize** the plan's phases and key decisions to the user.
3. **Run open-question protocol** — if the plan contains open questions, run the protocol above.
4. **Ask for explicit `approve`** — only after protocol completion (or if the plan has no open questions).
5. Approve → execute. Revise → re-engage SAGE. Reject → stop and report.

**STOP: The Plan Gate appears only after open questions are handled. Await `approve` before proceeding to phased execution.**

---

## Phased Execution

When executing a plan from SAGE:

1. **Parse** phase annotations — identify which tasks are parallel and which are sequential.
2. **Execute by phase** — apply the Parallel Dispatch rule above. Dispatch all parallel tasks in a phase in a single batched response. Sequential tasks go one at a time.
3. **Checkpoint** — after each phase completes, write state to `/memories/session/` (per the Session Resumption Protocol in `AGENTS.md`): active spec folder, completed phase IDs, remaining phases, blockers, decisions. Do this before starting the next phase.
4. **Report** — brief status update after each phase.
5. **Verify** — confirm success criteria are met after all phases complete.
6. **Clean up** — engage MERLIN to archive any temp agents hired for the effort.

---

## Hiring Protocol

When no existing agent fits a task:

1. Invoke MERLIN with the role requirements and task context.
2. MERLIN engages SCOOP for skills research, then creates the agent.
3. Decide: **permanent hire** (reusable expertise across projects) or **temporary** (one-time task).
4. After the temp agent's work is done, MERLIN moves its file to `.github/agents/temps/` and updates the roster.

> For the rule on not authorizing agents to skip required processes, see `.github/agents/arthur.agent.md` § Constraints.

---

## Artifact Location

### Short-name generation rules

ARTHUR generates the short name from the user's request:

- 2–4 words, kebab-case
- Action-noun where possible (`user-auth`, `fix-payment-timeout`)
- Preserve technical terms and acronyms (`oauth2`, `api`, `jwt`)
- Concise but descriptive

**Short-name examples** — Four annotated examples mapping user requests to spec folder names.
1. Read `references/worked-examples.md` § short-name-examples.

### Folder procedure

1. Tell SAGE which folder to use (e.g., "use `artifacts/spec004-fix-payment-timeout/`").
2. When dispatching other agents in the same effort, reference the same spec folder in their brief.
3. Multiple efforts may run in parallel in different spec folders.

---

## Error Recovery

> For error recovery procedures (task failure, plan invalidation, conflicting results, stuck, agent interrupted), see `.github/agents/arthur.agent.md` § Error Recovery.

---

## Worked examples

**Worked examples** — Six DO/DON'T pairs covering: multiple research topics, narration without dispatch, explicit path request, simple task delegation, parallel vs sequential dispatch, and Spec Checkpoint skip.
1. Read `references/worked-examples.md` for DO/DON'T examples.

---

## Quick reference

- **Who did I dispatch?** → Roster check first, every time.
- **One topic or many?** → Count independent topics before briefing. One brief per task.
- **Parallel or sequential?** → Independent + no shared files = parallel in one batched response.
- **Any generated doc with open questions?** → Follow **Human Checkpoints → Open-question protocol** (canonical); do not invent variants.
- **Spec or plan checkpoint?** → Follow **Human Checkpoints → Spec Checkpoint / Plan Checkpoint** (canonical) and hold the gate there.
- **Something failed?** → See `.github/agents/arthur.agent.md` § Error Recovery.
- **PROBE run or LENS dispatch?** → Read `references/testing-protocol.md`.
