# Memory Fallback — Full Detail

> This file covers degraded-mode operation when the Copilot memory tool is unavailable. The normal memory protocol is in `AGENTS.md`. Read this file only when you have confirmed the memory tool is unavailable at session startup.

---

## Fallback Root

When the memory tool is unavailable, all reads and writes use a local on-disk fallback rooted at `.agent-memory/` in the workspace:

```
.agent-memory/
├── session/   # session-scoped notes (equivalent to /memories/session/)
└── repo/      # repo-scoped notes (equivalent to /memories/repo/)
```

**No user scope in fallback.** User memory lives in VS Code's `globalStorage`, which is unreachable from the workspace. Degraded agents operate without user-scope memory.

**Gitignored.** `.agent-memory/` is listed in `.gitignore` — fallback notes never leak into commits.

---

## Detecting Degraded Mode

At session startup, probe memory tool availability by calling `view /memories/session/`.

- **If the probe succeeds:** Memory tool is available. Use `/memories/` paths throughout the session.
- **If the probe fails:** Memory tool is unavailable. Switch to `.agent-memory/` paths. Prepend `[no-memory]` to your first reply this session (see below).

Mode is determined **once at startup and is sticky for the session**. Do not re-probe mid-session. Do not switch backends mid-session.

---

## `[no-memory]` Notification Rule

When you detect memory unavailability at startup and switch to fallback mode:

1. Prepend `[no-memory]` to your final reply **exactly once** this session.
2. Immediately write the sentinel file: `.agent-memory/.notified-this-session`
3. On all subsequent replies this session: check for the sentinel file. If it exists, do NOT prepend `[no-memory]` again.

**Sentinel file:** `.agent-memory/.notified-this-session`

- Created immediately before returning the first degraded reply.
- Its presence means the user has already been notified this session.
- The sentinel is session-scoped by convention. A new conversation re-evaluates availability and, if still degraded, re-creates the sentinel and re-notifies on its first reply.

---

## Mid-Session Memory Flicker

- If memory was **available at startup** and becomes unavailable later: continue as if memory is available. Do not switch to fallback. Do not prepend `[no-memory]`.
- If memory was **unavailable at startup** and becomes available later: continue operating in fallback mode against `.agent-memory/`. Do not migrate. Do not re-probe.

This prevents inconsistent behaviour, partial writes split across both backends, and repeated user-facing notifications within a single conversation.
