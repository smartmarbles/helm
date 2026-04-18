### Startup Memory Probe

At session start, perform exactly **one** probe: call `memory view /memories/session/`. The outcome of this single call determines your memory mode for the entire session.

**Memory available** (the call succeeds): operate in memory mode — write session and handoff state to `/memories/session/<agent>-<slug>.md`, and write durable knowledge to `/memories/repo/`.

**Memory unavailable** (the tool is absent or the call errors): operate in fallback mode — write session and handoff state to `.agent-memory/session/<agent>-<slug>.md`, write durable knowledge to `.agent-memory/repo/`, and prepend `[no-memory]` to your first response of the session (once per session, per FR-016).

**Sticky mode**: the probe runs **once at session start**. The resulting mode is sticky for the remainder of the session — do not re-probe mid-session, and do not switch modes if a later call happens to succeed or fail.

`<agent>` is parameterized: substitute the lowercase agent name (e.g., `arthur`, `sage`, `quill`). `<slug>` is a short kebab-case task identifier chosen by the agent.
