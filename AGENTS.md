# Helm AI Team — Workspace Context

This workspace uses an AI team orchestration system. All agents should be aware of the team structure and operating protocols described here.

## Team Structure

- **Roster**: `.github/team-roster.md` — all active and archived members
- **Agents**: `.github/agents/*.agent.md` — permanent team members
- **Temps**: `.github/agents/temps/` — completed temporary agents

## When Operating as a Specific Agent

When a user selects a specific agent (SCOOP, SAGE, QUILL, MERLIN, etc.), follow that agent's own instructions. The team structure above is context — not a directive to override the selected agent's behavior.

## Artifacts

Project artifacts (specs, plans, research, tasks) live in `artifacts/spec###-short-name/` folders, numbered sequentially with a descriptive kebab-case suffix (e.g., `artifacts/spec004-user-auth/`). Check `artifacts/` for existing `spec###-*` folders before creating new ones.

Standalone documentation (not tied to a spec workflow) lives in `artifacts/docs/`.

**Ownership**: ARTHUR assigns spec folder names and numbers. SAGE creates the folders. All other agents write to the folder specified in their task brief — never create spec folders themselves.

## Memory

- Repo memory (`/memories/repo/`) — persistent project knowledge shared across sessions
- Session memory (`/memories/session/`) — in-progress task context for the current conversation

---

# Session Resumption Protocol

This protocol applies to all agents. Follow it on every task.

## Before Starting Any Task

1. Check `/memories/session/` for in-progress work from a prior session. If a checkpoint exists, resume from the recorded position rather than starting over.
2. Check `/memories/repo/` for persistent project conventions, patterns, and key decisions that should inform your work.
3. **ARTHUR only:** Also check `artifacts/` for spec folders with unchecked tasks in `plan.md` or `tasks.md`. If active work exists, summarize state and ask the user whether to continue or start fresh. Other agents skip this step.

## While Working

Checkpoint proactively after each major unit of completed work — don't wait until the task is done. A checkpoint is a write to `/memories/session/` that records enough state to resume cleanly if the session ends unexpectedly.

At minimum, every checkpoint should include:
- What you're working on (task description, target files or spec folder)
- What is complete (section names, phase IDs, file paths written so far)
- What remains (the outline or task list of incomplete work)
- Key decisions made so far that would affect the remaining work

Each agent's definition file specifies the additional checkpoint detail relevant to that agent's work.

## After Completing a Task

- Clear or update `/memories/session/` so stale state doesn't mislead a future session.
- For ARTHUR: after completing a Standard or Full Path effort, save reusable discoveries (conventions, patterns, key file locations) to `/memories/repo/`.
