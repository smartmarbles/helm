# P2-T3 — Fallback Directory Structure, Gitignore, and Notification Sentinel

Staged content for ARTHUR to merge into `AGENTS.md` and `.gitignore`.

Covers: **FR-015**, **FR-016**, **FR-021**.

---

## 1. Gitignore Directive

Add the following to `.gitignore` (exact, ready to paste):

```gitignore
# Local fallback memory used when Copilot memory tool is unavailable (spec002)
.agent-memory/
```

---

## 2. Fallback Structure Prose (for AGENTS.md)

Insert the following subsection under the existing **Memory Scope Convention** section in `AGENTS.md`.

---

### Fallback Memory Structure

When the Copilot memory tool is unavailable at session startup, agents degrade to a local on-disk fallback rooted at `.agent-memory/` in the workspace. The fallback mirrors the repo and session scopes only:

```
.agent-memory/
├── session/   # session-scoped notes (equivalent to /memories/session/)
└── repo/      # repo-scoped notes (equivalent to /memories/repo/)
```

**No user scope.** User memory lives in VS Code's `globalStorage`, which is not reachable from the workspace. There is no safe way to fake it locally, so degraded agents operate without user-scope memory. (FR-021)

**Why only session + repo.** Both map cleanly to workspace-relative directories, are safe to write from any agent, and are already scoped to the current project. User memory's cross-workspace persistence cannot be replicated without access to the Copilot memory tool.

**Gitignored.** `.agent-memory/` is listed in `.gitignore` so fallback notes never leak into commits.

#### `[no-memory]` Notification Rule

When an agent detects memory unavailability at startup and falls back to `.agent-memory/`, it must inform the user that it is operating in degraded mode:

- **Prepend `[no-memory]` to the agent's final reply exactly once per session.**
- After the first prepend, a sentinel file is written to suppress further prepends for the remainder of the session.

**Sentinel file:** `.agent-memory/.notified-this-session`

- Created on the first degraded reply, immediately before returning.
- Its presence signals "user has already been notified this session" — subsequent replies in the same session MUST NOT prepend `[no-memory]` again.
- The sentinel is session-scoped by convention. A fresh session (new conversation) starts by re-evaluating memory availability and, if still degraded, will re-create the sentinel and re-notify on its first reply.

#### Mid-Session Memory Flicker

Memory tool availability is evaluated **once at session startup** and the result is sticky for the life of the session.

- If memory was available at startup and becomes unavailable later in the session, agents continue operating as if memory is available. They do not switch to fallback mid-session and do not prepend `[no-memory]`.
- If memory was unavailable at startup and becomes available later, agents continue operating in fallback mode against `.agent-memory/`. They do not migrate or re-probe.
- **Agents do not re-probe memory availability mid-session.** Mode is detected at startup and remains fixed until the session ends.

This prevents inconsistent behaviour, partial writes split across both backends, and repeated user-facing notifications within a single conversation.

---

## Acceptance Checklist

- [x] `.gitignore` line is exact and paste-ready (`.agent-memory/` with one-line comment).
- [x] Sentinel rule explicitly states "exactly once per session."
- [x] Sentinel file path specified: `.agent-memory/.notified-this-session`.
- [x] Flicker rule explicit: "agents do not re-probe"; mode is sticky per session.
- [x] No user scope in fallback layout (FR-021 honoured).
