# Run Test Plan

Execution detail for PROBE. The agent file defines *who PROBE is* and the epistemic stance ("report what IS, not what should be"); this skill defines *how PROBE runs a test* — the execution protocol, stream-capture mechanics, assertion checks, violation recording, scorecard population, cleanup, and report format.

Read this skill whenever a request asks PROBE to execute tests, run a smoke pass, or verify behaviour against the test plan. If you are PROBE and you are about to run anything, you must already be inside this skill.

## How to use this skill

0. **Complete model verification first** — read the `design-test-rubric` skill's three-layer model-verification protocol and record all three layers in the run report's `## Verification` section before making any other tool call. Layer 3 is non-interactive: record the model slug from the brief (or `unknown` if omitted) — no handoff prompt, no user confirmation. No test-plan reads, no file listings, no snapshots, no subagent dispatches until all three layers are recorded. This is a hard ordering constraint.

   **Permitted before Layer 1 (setup reads only)**: reading this skill file and `artifacts/testing/probe-report-template.md`. These are structural setup reads, not investigative tool calls, and do not trigger an ordering violation. All other reads (test plan, rubric, agent files, workspace listings) must follow all three layers.

   > **Ordering violation self-report:** If model verification was skipped or partially completed before proceeding, record it explicitly in the run report's Verification section and note which test cases were affected. Do not silently proceed.
1. **Accept the command** (`run TC-XXX`, `run category X`, `run agent AGENT`, `run smoke`) — parse scope.
2. **Verify clean working tree** — run `git status --short`. If the output is not empty, **stop immediately** and tell the user:
   > ⛔ Working tree is not clean. Commit or stash all changes before running tests — PROBE uses `git status` to detect test artifacts, and a dirty tree makes that unreliable.
   Do not proceed until the user confirms the tree is clean.
3. **Load the test plan** at `artifacts/testing/test-plan.md` and the pre-existing scorecard (if the run targets one).
4. **Read the Summary Checklist** — located near the bottom of the test plan under the heading `## Summary Checklist`. This is the authoritative source for each test's mode and category membership. Build your run list from it before reading individual test bodies. Never infer mode from icons in the test body.

   **For `run category X` commands**: find the category X sub-section in the Summary Checklist (e.g., `### X — ...` or the rows grouped under the `X` category label). Collect only the TC rows explicitly listed under that sub-section. Do NOT infer membership by TC-number proximity or contiguous range — a category's TCs may be non-contiguous. The checklist rows are the definitive membership list.

   - **🤖** — fully automatable. Run all pass criteria.
   - **👤** — skip the entire test: `⏭️ SKIP — manual test, requires human execution`.
   - **🤖/👤** — partial. Run ONLY the `**🤖 Automatable Portion**` criteria. Skip `**👤 Manual Portion**` criteria: `⏭️ SKIP — manual criteria, requires human execution`.

   > **Exact phrase required**: The skip phrases above must appear verbatim in your output for each skipped test or criterion — do not abbreviate (e.g. `⏭️ SKIP | 👤 manual` is invalid). For 🤖/👤 tests, each 👤 criterion must individually carry `⏭️ SKIP — manual criteria, requires human execution`. Do not collapse these into table notation or omit them from table cells.
   >
   > **Per-criterion rows required for 🤖/👤 tests**: The result table must have one row per criterion — even when an automatable criterion fails. A FAIL row for criterion [4] and a SKIP row for criterion [5] are both required and must appear as separate table entries. Do **not** collapse both into a single row. Example of correct output for a mixed test where criterion [4] fails and criterion [5] is manual:
   >
   > | Criterion | Result | Evidence |
   > |-----------|--------|----------|
   > | **[4]** automatable criterion | ❌ FAIL \| V-001 (critical) | … |
   > | **[5]** manual criterion | ⏭️ SKIP — manual criteria, requires human execution | 👤 manual |

5. **Execute each test** via the Execution Protocol — snapshot → run → evaluate → check side effects → record → clean up.
6. **Capture streams** for any shell or tool command using the Stream Capture rules.
7. **Record violations** into the Violation Log using the schema below — observed, not inferred.
8. **Populate the scorecard** with what was observed (severity/weight come from the rubric; *filling it in* is execution).
9. **Report** with the pass/fail summary format and sign off with the one-line tally.

---

## Execution Protocol

Every automatable test follows these seven steps. Do not reorder. Do not skip a snapshot to "save a turn".

1. **Announce** — `Running TC-XXX: [name]...`
2. **Read the test** from the test plan to get the exact input prompt and pass criteria. Do not rely on a registry table alone for pass criteria.
3. **Snapshot** pre-test state relevant to the test. Use the cheapest signal that gives an unambiguous diff:
   - **Artifact tests** — run `git status --short` and confirm the output is empty before dispatching. If not clean, a previous test's cleanup failed — halt, report the dirty paths, and do not proceed until resolved.
   - **Hiring tests** — run `Get-ChildItem .github/agents/ -Filter "*.agent.md" | Select-Object -ExpandProperty Name` (names only, not contents).
   - **Memory tests** — use the `memory` tool to view `/memories/session/` and `/memories/repo/`.
   - `/memories/` paths are VS Code virtual paths accessed via the `memory` tool — they are NOT physical folders. A `memories/` folder appearing in the workspace filesystem is contamination.
4. **Execute** — invoke the target agent as a subagent with the *exact* input prompt from the test plan. For shell/tool tests, run the command and capture streams (see Stream Capture below).
5. **Evaluate** the response against each pass criterion. For each criterion, determine PASS or FAIL and record the specific evidence observed — quote the relevant response excerpt, tool call name, or file content. Evidence is required for every criterion regardless of pass or fail. A criterion row with no evidence is invalid and must be treated as UNVERIFIABLE.
6. **Check side effects** on the file system when the test requires it.
7. **Clean up** (see Cleanup Protocol) and **record** the result.

### Rule: one failed criterion fails the whole test

A test passes only if ALL pass criteria are met. Do not round up, do not "mostly pass" a test. Partial credit is a rubric-design concern, not an execution call.

### Rule: report what IS, not what should be

PROBE records observations, not judgments. If an agent's output is ambiguous, record exactly what appeared (quote it if possible). Do not decide what the agent "meant to do". The rubric and the user decide interpretation; PROBE supplies facts.

---

## Input Commands

| Command | Scope |
|---------|-------|
| `run TC-XXX` | One test by ID |
| `run category X` | All 🤖 and 🤖/👤 tests in a category (e.g., `run category E`) |
| `run agent AGENT` | All 🤖 and 🤖/👤 tests whose Agent column matches AGENT (e.g., `run agent SCOOP`, `run agent SYSTEM`) |
| `run smoke` | Only the 🤖 and 🤖/👤 tests in the Smoke Test set |
| `Finalize <report_file>` | Tally and append final summary to an in-progress report |

> **Note:** `run all` is no longer a valid PROBE command. Full-suite runs are orchestrated by ARTHUR, which dispatches PROBE once per category. PROBE always receives a scoped brief — never `run all`.

> **Self-referential exception:** `run category N` and `run agent PROBE` cannot be handled by PROBE — PROBE cannot be both runner and subject. These commands must be routed to ARTHUR, who dispatches PROBE with each test's input and then dispatches LENS to evaluate the output. If PROBE receives either command directly, it must refuse and explain that ARTHUR is the required runner for category N.

> **Category batch limit (for orchestrators):** Before dispatching `run category X`, check the Summary Checklist for that category's automatable test count. If the count exceeds 8, split into sequential sub-dispatches of ≤8 automatable tests each. Supply the same `Report file:` path to each sub-dispatch (append mode after the first). Label each sub-dispatch clearly in the brief (e.g., "run category X tests TC-nnn–TC-mmm", then "run category X tests TC-nnn–TC-mmm").

👤 (manual) tests are NEVER run. Report them as `⏭️ SKIP — manual test, requires human execution` and move on.

---

## Evaluation Rules

When evaluating an agent's response against pass criteria:

- **Response content checks** — does the response contain or not contain specific content? (e.g., "includes a `What Most People Miss` section" → grep the response).
- **Delegation checks** — did the agent delegate vs. do the work itself? (e.g., "ARTHUR does not produce findings" → check whether the response contains research prose vs. a delegation brief and a `runSubagent` call).
- **Refusal checks** — did the agent refuse an out-of-scope request? (e.g., "SAGE does not produce TypeScript code" → scan for code fences).
- **File-system checks** — were files created / not created? (e.g., "no folder created under `artifacts/`" → diff pre-test snapshot vs. post-test listing).
- **Structure checks** — does the response follow the expected format? (e.g., expected headings all present and in order).
- **Exit-code checks** — for tool/CLI tests, the captured exit code matches the expected value.
- **Stream-content checks** — captured stdout / stderr contains or does not contain expected patterns.
- **Delegation chain rule**: When a pass criterion names a specific agent's output (e.g., "SCOOP's report includes X", "MERLIN's file contains Y"), evaluate that agent's raw subagent result — not any orchestrator's relay or summary of it. In a `runSubagent` execution chain, the subagent's `result` field is the authoritative evidence source for criteria that name that agent.

---

## Stream Capture

When a test runs a shell command, CLI, or tool (e.g., `validate_skill.py`, a build script), stdout and stderr must be captured **separately** and **as raw byte streams**, not via PowerShell's pipeline. Pipeline capture re-encodes output and can corrupt non-ASCII characters and interleave streams.

### PowerShell pattern (required for Windows test runs)

```powershell
$out = New-TemporaryFile
$err = New-TemporaryFile
$p = Start-Process -FilePath python `
    -ArgumentList '.github\scripts\validate_skill.py','.github\skills\skill-creator' `
    -NoNewWindow -Wait -PassThru `
    -RedirectStandardOutput $out `
    -RedirectStandardError  $err
$exit   = $p.ExitCode
$stdout = Get-Content $out -Raw
$stderr = Get-Content $err -Raw
Remove-Item $out, $err
```

Record `$exit`, `$stdout`, and `$stderr` as three separate fields in the test log. Do not concatenate them.

**Why not `2>&1` piping** — Rationale for why merged-stream piping loses the stdout/stderr distinction that assertions depend on, and why separate temp-file redirection is required instead.
1. Read `references/stream-capture-rationale.md` for the full rationale.

### Appending to the test-log artifact

After capturing streams, append a fenced code block per stream to the test's log section in the spec's smoke-test log file (e.g., `artifacts/spec002-agent-system-hardening/frontmatter-allowlist-audit.md` for P9a-T4), with `stdout:` and `stderr:` labels. Empty streams are recorded as `(empty)`, not omitted — absence is a finding.

---

## File-System Assertions

For tests that assert on workspace state:

1. **Pre-test snapshot** — list the target directory (or run the `memory` tool `view` command on the target memory path) and store the listing.
2. **Post-test listing** — list the same directory after execution.
3. **Diff** — compute added / removed / modified entries.
4. **Match against the pass criterion** — e.g., "no folder created under `artifacts/`" means the diff has zero `A artifacts/**` entries.
5. **Content assertions** — when a criterion names expected content (e.g., "frontmatter contains `description:` field"), read the created file and check the pattern. Record the exact matched line, not "yes it was there".

### Rule: never write to a pre-existing file (except cleanup)

PROBE may only write to files that **did not exist before the test started**, with two exceptions:
1. The active run's report file under `artifacts/testing/reports/` (PROBE created it at run start).
2. **Cleanup only**: removing content that a dispatched subagent added to a pre-existing file during the test (e.g., removing a `TEST-` row from `team-roster.md`). This exception applies strictly to cleanup — not to test execution, evaluation, or any other phase.

**Before issuing any write tool call** (create_file, replace_string_in_file, etc.) outside of cleanup, check: was this file present in the pre-test snapshot? If yes and it is not the active run's report file — **STOP.** Do not write. Report:

```
⚠️ CONTAMINATION PREVENTED: PROBE attempted to write to pre-existing file [path] during TC-XXX. Run halted.
```

If a pre-existing file was already modified outside of cleanup before this check fired, report it as:

```
⚠️ CONTAMINATION: [path] was modified by TC-XXX outside of cleanup. Run halted.
```

Do NOT revert it. The damage is the test's fault, not PROBE's. Reverting risks destroying legitimate concurrent work. Stop the run immediately — do not continue to the next test case.

---

## Violation Log

When a pass criterion fails or a side-effect check surfaces unexpected behaviour, append an entry to the Violation Log for the run. The entry records what was observed; severity and weight come from the rubric (authored via the `design-test-rubric` skill).

Schema per entry:

| Field | Required | Notes |
|-------|----------|-------|
| `test_id` | yes | e.g., `TC-029` |
| `criterion` | yes | Verbatim text of the failed pass criterion |
| `expected` | yes | What the criterion required |
| `actual` | yes | What was observed — quote the response excerpt, file path, or stream fragment |
| `severity` | yes | One of the rubric's severity tiers (critical / major / minor). PROBE applies the rubric's rules; PROBE does NOT invent new tiers. |
| `category` | yes | The rubric's scoring category this violation maps to |
| `evidence` | yes | Pointer to captured evidence: response snippet, log file path + line, screenshot path |

### Rule: no invented severity

If the rubric does not have a rule that fits an observation, record the observation verbatim under `actual` with `severity: unclassified` and flag it in the report. Do not guess. Severity design is a rubric concern.

---

## Scorecard Population

The scorecard *schema* is defined by the rubric (see the `design-test-rubric` skill). *Filling it in* is execution work:

> **Required format:** All PROBE report files MUST follow the canonical template at `artifacts/testing/probe-report-template.md`. Read that file before authoring any new report. LENS validates that the `run_type` and `chat_log` frontmatter fields are present — reports missing these fields will be rejected by LENS and treated as pre-template artifacts.

> For `chat_log`: record the filename as provided in the dispatch brief (e.g., `chat-sonnet46-20260502.json`). If the filename was not supplied in the brief, write `"unknown — provide before LENS audit"`. Do NOT substitute the session UUID — LENS cannot locate a file by UUID.

1. Copy the canonical template from `artifacts/testing/probe-report-template.md` for the new run. Name the output file `artifacts/testing/reports/probe-<run_type>-<model>_<YYYY-MM-DD>-<seq>.md` where `<seq>` is a two-digit sequence number starting at `01` (e.g., `probe-baseline-gpt41_2026-04-22-01.md`). To determine `<seq>`, list `artifacts/testing/reports/` and find the highest existing sequence number for files matching `probe-<run_type>-<model>_<YYYY-MM-DD>-*.md` on that date, then increment by 1. If no matching files exist, use `01`. Replace all `{{PLACEHOLDER}}` values with run-specific data.

   > For time fields (`run_start`, `run_end`, `run_duration`): the system context only injects the current **date**, not the time. To get the wall-clock time, run `Get-Date -Format 'yyyy-MM-ddTHH:mm:ss'` in a terminal. Record the result. Never write `"n/a"`, fabricated, estimated, or placeholder timestamps.

2. For each scoring category in the scorecard, tally the pass/fail tests and violations whose `category` field targets it.
3. Copy each violation's `expected`/`actual`/`evidence` into the scorecard row for its test. Do not paraphrase.
4. Leave subjective / narrative cells empty if the observation doesn't speak to them — do NOT fabricate commentary.
5. Compute the totals only with the arithmetic the rubric specifies. If the rubric is silent on a case, leave the cell as `—` and note it in the report.

---

## Multi-Dispatch Append Behavior

When PROBE is dispatched as one category in a batched `all` run (orchestrated by ARTHUR), the brief will include a `Report file: <path>` field and one of two modes:

- **Create mode** (category A, or when the file does not exist): Copy the canonical template from `artifacts/testing/probe-report-template.md`, replace all `{{PLACEHOLDER}}` values with run-specific data, and write it to `artifacts/testing/reports/` at the named path. Then append this category's results.
- **Append mode** (categories B–O): Open the existing file. Append this category's result rows to the Results Table and any new violations to the Violation Log. Do NOT overwrite or re-create the header, frontmatter, or sections already written.

When you receive a `Finalize <report_file>` brief: read the full report file, tally pass/fail counts across all result rows, and append the consolidated scorecard totals and the one-line sign-off (`X/Y passed. Z failures.`) to the report.

**Rule: never re-create an existing report file.** If the file already exists and the brief says append, append only. Overwriting destroys prior categories' results.

**Rule: update scope and timestamps on every append.** When appending to an in-progress report:
- Update the `scope` frontmatter field to include the newly completed TC IDs (accumulate across all dispatches — do not overwrite with only the current category's TCs).
- Update the Run Context section's end-time field to the current timestamp.
- Set `run_start`, `run_end`, and `run_duration` from the actual wall-clock time. Run `Get-Date -Format 'yyyy-MM-ddTHH:mm:ss'` in a terminal to get the current time — do not guess or estimate. Never write `"n/a"`, estimated, or fabricated timestamps.
- Never leave `{{PLACEHOLDER}}` values in the report after your dispatch — replace all of them with actual values on create, and update any that remain stale on append.

**Rule: never update a past run's report file.** Each new test run produces a new file (with an incremented sequence number). Do not append results from a new run to a report file from a previous run, even if the run type, model, and date match. If the file already exists and this is a new run (not a multi-dispatch continuation), increment the sequence number and create a new file.

---

## Cleanup Protocol

**CRITICAL: Clean up after every test. No exceptions.**

After each test, restore the workspace:

- Delete any **new files** created in `artifacts/` during the test.
- Delete any **new** `.agent.md` files created in `.github/agents/` during the test.
- Use the `memory` tool `delete` command to remove entries created in `/memories/session/` or `/memories/repo/` during the test.
- If a folder was created (e.g., a new spec folder), delete the entire folder.
- If a `memories/` folder was created in the workspace filesystem, delete it — that is contamination, not valid state.
- Delete any temp files used for stream capture (`$out`, `$err` above).
- Verify cleanup by re-listing the affected directories and diffing against the pre-test snapshot.

### Rule: never use git for cleanup

**NEVER use `git checkout`, `git restore`, `git stash`, or any git command for test cleanup.** These revert ALL uncommitted changes, destroying legitimate in-progress work that predates the test run. Delete specific files by path using the file-system tools. If you are not sure which files the test created, re-run the diff.

### Rule: stop on cleanup failure

If cleanup cannot be completed, report it explicitly:

```
⚠️ CLEANUP FAILED: [what remains, full paths]
```

Stop the run. A stale artifact from TC-001 will corrupt TC-052. Do not continue into the next test.

---

## Report Format

**Single-scope dispatches** (`run smoke`, `run TC-###`, standalone `run category X` without a `Report file:` brief): produce the full inline report after all tests in scope complete:

```
## Test Report — [date]

**Scope**: [what was run — "category E", "TC-029", "smoke", etc.]
**Result**: X/Y passed. Z failures.

| ID | Name | Result | Details |
|----|------|--------|---------|
| TC-XXX | [name] | ✅ PASS | |
| TC-YYY | [name] | ❌ FAIL | [brief: expected vs. actual] |
| TC-ZZZ | [name] | ⏭️ SKIP | Manual test |
| TC-AAA | [name] | ⚠️ ERROR | [what went wrong] |

### Failures

#### TC-YYY — [name]
- **Expected**: [what should have happened]
- **Actual**: [what did happen]
- **Pass criteria failed**: [which specific criteria]
- **Evidence**: [pointer to log file, response excerpt, or captured stream]

### Violation Log
[full schema entries for every failure, per the Violation Log section above]

### Cleanup Status
All test artifacts cleaned up successfully.
```

Sign off with the single-line tally: `X/Y passed. Z failures.`

**Multi-dispatch category runs** (brief includes `Report file: <path>`): do NOT produce a full inline report. Append this category's result rows to the report file per the Multi-Dispatch Append Behavior section, then confirm inline with a single line: `Category {X} complete — {n} passed, {m} failed. Results appended to {report_file}.`

---

**Worked examples** — Four annotated DO/DON'T pairs covering stream capture, file-system assertion, unclassified severity, and git cleanup.
1. Read `references/worked-examples.md` for DO/DON'T examples.

---

## Quick reference

- **Which tests?** → 🤖 and 🤖/👤. 👤 → SKIP. For 🤖/👤, run only the `🤖 Automatable Portion` criteria; skip `👤 Manual Portion` criteria.
- **Pass criteria?** → Read from the plan, not the registry. ALL must pass.
- **Stream capture?** → `Start-Process -RedirectStandardOutput/-RedirectStandardError` to separate temp files. Never `2>&1`.
- **File assertion?** → Pre-test snapshot, post-test listing, diff. No shortcuts.
- **Violation severity?** → Rubric rule applies, or `unclassified`. Never invent.
- **Cleanup?** → Specific paths, verify with diff. NEVER `git checkout`.
- **Cleanup failed?** → Stop the run, report, escalate.
- **Report (single-scope)?** → Full inline summary table + Failures + Violation Log + Cleanup Status + one-line tally.
- **Report (multi-dispatch category)?** → Append to report file only. One-line inline confirmation.
- **Report (Finalize)?** → Read report file, tally all rows, append scorecard totals + one-line sign-off.
