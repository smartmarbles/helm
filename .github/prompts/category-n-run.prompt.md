---
description: "Run category N (PROBE Protocol) tests. Usage: /category-n-run <run-type> [model=<slug>] [tc=TC-###]. Examples: /category-n-run baseline | /category-n-run regression model=gpt-4.1 | /category-n-run baseline tc=TC-085"
---

You are ARTHUR. Category N cannot be delegated to PROBE — PROBE cannot be both runner and subject. You will run this category yourself using the protocol below.

---

**Step 1 — Parse invocation arguments.**

Check the user's message for:
- A **run type**: `baseline`, `regression`, or any custom label — **required**
- A **model override** (optional): `model=<slug>` (e.g. `model=gpt-4.1`)
- A **single TC override** (optional): `tc=TC-###` (e.g. `tc=TC-085`) — if provided, run only that one test instead of all six

If no run type was provided, stop and ask:
> What run type is this? (e.g. `baseline`, `regression`, or a custom label)

Do not proceed until a run type is confirmed.

Set `{tc_list}` based on the arguments:
- If `tc=` was provided: `{tc_list}` = that single TC (e.g. `[TC-085]`)
- Otherwise: `{tc_list}` = `[TC-084, TC-085, TC-086, TC-087, TC-088, TC-089]`

**Step 2 — Load the testing protocol.**

Read `.github/skills/orchestrate-delegation/references/testing-protocol.md` in full before proceeding. The Category M section defines the exact execution steps. Follow it throughout.

**Step 3 — Read the category N tests.**

Read `artifacts/testing/test-plan.md`, section `## N — PROBE Protocol` (TC-084 through TC-089). For each test, locate the `Test Input (PROBE receives this)` block — that is the brief you will pass to PROBE verbatim.

**Step 4 — Determine the report filename.**

List `artifacts/testing/reports/` and find the highest existing sequence number for files matching `probe-{run_type}-{model}_{YYYY-MM-DD}-*.md` on today's date, then increment by 1. If none exist, use `01`.

`artifacts/testing/reports/probe-{run_type}-{model}_{YYYY-MM-DD}-{seq}.md`

Check whether this file already exists (i.e., category M is being appended to an in-progress full run):
- If it **does not exist**, instruct PROBE to create it from the template at `artifacts/testing/probe-report-template.md` on its first dispatch, replacing all `{{PLACEHOLDER}}` values.
- If it **already exists** (category M is being appended to an in-progress full run), instruct PROBE to append to it on every dispatch.

**Step 5 — Dispatch PROBE once per TC in `{tc_list}`.**

For each TC in `{tc_list}` — in order — send PROBE this brief (substitute values before sending):

> Run `{TC-###}` from the test plan (`artifacts/testing/test-plan.md`). Run type: `{run_type}`. Model: `{model}`. Rubric: read the current version from the latest entry in §8 of `artifacts/testing/probe-scoring-rubric.md`.
> Report file: `{report_file}`.
> - {create or append instruction per Step 4}
> Follow the run-test-plan skill throughout. Clean up after the test.
> The test input is: `{paste the exact Test Input block from the TC body}`

Do not batch. Wait for each PROBE dispatch to complete before sending the next.

If **TC-089 is in `{tc_list}`** and it is the final dispatch, append this additional instruction to its brief:
> After appending TC-089 results, update the Run Context section of the report to reflect the full scope of this run: all tests in `{tc_list}`. Replace any single-TC scope description left by the first dispatch.

**Step 6 — Verify the results file.**

After all dispatches in `{tc_list}` complete, use `read_file` (not `file_search`) to confirm the report file exists at the expected path. `read_file` queries the filesystem directly; `file_search` uses a workspace index that may be stale after a subagent write and can produce false negatives. If `read_file` returns an error or empty content, re-engage PROBE — do not proceed on prose confirmation alone.

**Step 7 — Post the export reminder and wait.**

Post this message verbatim:

> ⚠️ **Manual step required before LENS can audit:**
> Export this session's chat log using **VS Code Chat: Export Chat** and save it to `artifacts/testing/chats/`. The exported `chat-*.json` contains the full tool call trace (`subAgentInvocationId`, `parentId` chain, `requests[N].response[M]` structure) that LENS requires to evaluate PROBE's behavior on {tc_list}. LENS cannot produce verified verdicts without it.
> Once exported, let me know and I'll dispatch LENS.

Wait for the user to confirm the export is in place before proceeding.

**Step 8 — Dispatch LENS.**

Once the user confirms the export, dispatch LENS with:
- The path to the exported `chat-*.json`
- The path to PROBE's results file (`{report_file}`)
- The instruction: `Audit PROBE's category M run. Verify {tc_list} using the exported chat log and PROBE's results file. Follow the audit-chat-log skill throughout.`
