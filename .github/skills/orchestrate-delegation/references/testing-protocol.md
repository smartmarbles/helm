# Testing Protocol

When dispatching PROBE to run test categories, apply standard phased execution rules — one PROBE dispatch per category brief.

## Standard category run (A–L, N, O)

After each category run completes:

1. **Verify PROBE's results file landed.** Use `read_file` or `file_search` to confirm the report exists under `artifacts/testing/` before proceeding. If absent, re-engage PROBE — do not proceed on prose confirmation alone.
2. **Post the export reminder** before dispatching LENS:

   > ⚠️ **Manual step required before LENS can audit:**
   > Export this session's chat log using **VS Code Chat: Export Chat** and save it to `artifacts/testing/chats/`. The exported `chat-*.json` contains the full tool call trace (`subAgentInvocationId`, `parentId` chain, `requests[N].response[M]` structure) that LENS requires. LENS cannot produce verified verdicts without it.
   > Once exported, let me know and I'll dispatch LENS.

3. **Wait for user confirmation** that the export is in place.
4. **Dispatch LENS** with the paths to both the exported `chat-*.json` and PROBE's results file.

## Category N — PROBE Protocol

Category N cannot be dispatched to PROBE as a single brief — PROBE cannot run its own category. Instead, ARTHUR runs each test individually:

1. **Read TC-084 through TC-089** from `artifacts/testing/test-plan.md` (category N section).
2. **For each TC**, dispatch PROBE with the `Test Input` block from that TC's body as the brief. Six separate dispatches — do not batch.
3. After all six dispatches complete, **verify PROBE's results file landed** (same rule as above).
4. **Post the export reminder** and wait for confirmation — the exported `chat-*.json` is the only source LENS can use to inspect PROBE's tool call sequence for these tests.
5. **Dispatch LENS** with the chat export and PROBE's results file.
