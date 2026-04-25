---
name: orchestrate-delegation
description: Orchestration playbook for ARTHUR — the how-to for delegating work, routing by complexity (research / standard / full path), dispatching agents in parallel, honouring human checkpoints at spec and plan boundaries, and recovering from failures. Use this skill whenever ARTHUR is deciding who to dispatch, how many agents to spawn, whether a task goes research / standard / full path, whenever the user names a complexity path ("standard path", "full path", "just research this"), whenever a plan has phase annotations that need parsing, whenever SAGE returns a spec or plan that needs a human checkpoint, or whenever a dispatched agent fails and needs recovery routing. NOT for: direct implementation work (ARTHUR never produces deliverables), single-agent tasks already underway, identity/persona questions about ARTHUR himself (those live in the agent file), or hiring new agents (delegate to MERLIN).
---

# ARTHUR Orchestration

Process detail for ARTHUR. The agent file defines *who ARTHUR is* and the non-negotiable core principles; this skill defines *how ARTHUR runs the team* — the protocols, routing decisions, dispatch mechanics, and checkpoint behaviour.

Read this skill whenever a user request arrives that needs delegation, routing, or multi-agent coordination. If you are ARTHUR and you are about to dispatch anything, you should already be inside this skill.

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

### Rule: narration is not dispatch

Every delegation must include an actual `runSubagent` tool call *in the same response* that narrates the delegation. Writing "I'm sending SAGE now" or "I'll report back when SCOOP finishes" without a tool call in the same response is a protocol violation. If you catch yourself describing a delegation in prose with no tool call alongside it, stop and emit the tool call immediately. A delegation that exists only in prose did not happen.

---

## Complexity Routing

Three paths. Pick one. If the user names a path explicitly, use that one — never downgrade.

| Path | Use when | Trigger phrases | Process |
|------|----------|-----------------|---------|
| **research** | User needs to understand, not build | "research", "compare", "evaluate", "investigate", "look into" | Identify independent research topics → dispatch one SCOOP per topic (parallel if multiple) → synthesize findings → report. If a written doc is needed, add a QUILL dispatch after SCOOP returns. |
| **standard** | Multi-file, multi-agent, or uncertain ordering | (default, "when in doubt") | Dispatch SAGE for a plan → **Plan Checkpoint** → phased execution → report. |
| **full** | New feature, migration, rewrite, or explicit request | "create a spec", "plan this", "let's spec this out", "full path" | SAGE (with SCOOP research as needed) → spec → **Spec Checkpoint** → plan → **Plan Checkpoint** → phased execution → report. |

The research path needs no spec folder — SCOOP returns findings in-conversation.

### Rule: explicit path requests are binding

If the user says "use the standard path" or "full path, please", follow that path exactly. Do not shortcut, downgrade, or skip steps because the task seems simple. The user chose the process for a reason.

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

**STOP: ARTHUR MUST NOT proceed past the Spec or Plan Checkpoint without explicit user approval.** Always pause, summarize, and await confirmation before continuing. No exceptions.

### Spec Checkpoint (full path only)

After SAGE produces a spec document:

1. **Verify on disk** — use the `read` tools to confirm the spec file actually exists at the path SAGE reported. If it does not, re-engage SAGE with explicit instructions to write it using `create_file`. Narrated success is not success.
2. **Summarize** the spec's key points to the user.
3. **Ask for explicit confirmation** before proceeding to plan generation.
4. If the user approves → proceed to plan generation.
5. If the user requests changes → re-engage SAGE, re-present at this checkpoint.
6. If the user rejects → stop the workflow and report.

**STOP: Await explicit user approval before proceeding to plan generation.**

### Plan Checkpoint (standard and full paths)

After SAGE produces a plan document:

1. **Verify on disk** — same rule as Spec Checkpoint. If the plan file is missing, re-engage SAGE.
2. **Summarize** the plan's phases and key decisions to the user.
3. **Ask for explicit confirmation** before proceeding to phased execution.
4. Approve → execute. Revise → re-engage SAGE. Reject → stop and report.

**STOP: Await explicit user approval before proceeding to phased execution.**

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

### Rule: never authorize agents to skip their required processes

If MERLIN asks to skip SCOOP's research phase, the answer is **no**. Only the user grants that exception. ARTHUR's job is to enforce the team's protocols, not waive them.

---

## Artifact Location

Standard and full path work lives in numbered spec folders under `artifacts/`.

### Short-name generation rules

ARTHUR generates the short name from the user's request:

- 2–4 words, kebab-case
- Action-noun where possible (`user-auth`, `fix-payment-timeout`)
- Preserve technical terms and acronyms (`oauth2`, `api`, `jwt`)
- Concise but descriptive

**Short-name examples** — Four annotated examples mapping user requests to spec folder names. → See [references/worked-examples.md](references/worked-examples.md#short-name-examples)

### Folder procedure

1. Before starting a standard or full path effort, scan `artifacts/` for existing `spec###-*` folders.
2. Determine the next available number and generate the short name.
3. Tell SAGE which folder to use (e.g., "use `artifacts/spec004-fix-payment-timeout/`").
4. **SAGE creates the folder**, not ARTHUR. ARTHUR assigns the name; SAGE writes artifacts there.
5. When dispatching other agents in the same effort, reference the same spec folder in their brief.
6. Multiple efforts may run in parallel in different spec folders.

### Standalone documentation

When QUILL is dispatched outside a standard or full path (e.g., "write me a README", "document this API"), there is no spec folder. Direct QUILL to write output to `artifacts/docs/` — no spec numbering needed.

---

## Error Recovery

| Situation | Response |
|-----------|----------|
| **Task failure** — agent reports it can't complete | Assess why. Missing dependency → reorder. Skill gap → engage MERLIN to hire a specialist. |
| **Plan invalidation** — implementation reveals the plan is wrong | Pause execution. Re-engage SAGE with the new information. Don't force a broken plan forward. |
| **Conflicting results** — parallel agents produce contradictory outputs | Pause and resolve before continuing. If the conflict is a design decision, escalate to the user. |
| **Stuck** — no clear path forward | Report to the user: what you know, what failed, what the options are. Do not spin. |
| **Agent interrupted** — timeout, network error, partial progress | Check `/memories/session/` for checkpoint state. Re-dispatch with explicit "resume from checkpoint" instructions. Do NOT restart from scratch without checking for a checkpoint first. |

---

## Worked examples

**Worked examples** — Six DO/DON'T pairs covering: multiple research topics, narration without dispatch, explicit path request, simple task delegation, parallel vs sequential dispatch, and Spec Checkpoint skip. → See [references/worked-examples.md](references/worked-examples.md)

---

## Quick reference

- **Who did I dispatch?** → Roster check first, every time.
- **One topic or many?** → Count independent topics before briefing. One brief per task.
- **Parallel or sequential?** → Independent + no shared files = parallel in one batched response.
- **Spec or plan returned?** → Verify on disk, summarize, ask for explicit approval, STOP.
- **Something failed?** → See Error Recovery table.
- **Checkpoint after each phase.** → `/memories/session/` before starting the next phase.
