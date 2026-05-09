---
description: "Run a LENS audit against a PROBE report and chat log. Usage: /lens-audit <probe-report-path> [chat-log-path]. Examples: /lens-audit artifacts/testing/reports/probe-baseline-gpt41_2026-05-01.md artifacts/testing/reports/chat-2026-05-01.json | /lens-audit artifacts/testing/reports/probe-baseline-gpt41_2026-05-01.md"
---

Delegate to LENS. Pass the following brief to LENS verbatim — do not summarize or reinterpret it. Substitute the actual file paths from the user's message before dispatching.

---

**Brief for LENS:**

Read `.github/playbooks/audit-chat-log/audit-chat-log.md` in full before doing anything else. Follow it throughout this audit.

**Step 1 — Identify inputs.**

The user has provided:
- **PROBE report**: `{probe-report-path}` — required
- **Chat log**: `{chat-log-path}` — provided if present; if omitted, check `artifacts/testing/chats/` for a `chat-*.json` file whose date matches the PROBE report's `run_date` frontmatter field and use it. If none can be matched, halt and ask the user to export and drop the chat log into `artifacts/testing/chats/` then provide the filename.

  > **Canonical drop location for exported chat logs:** `artifacts/testing/chats/`. Export via VS Code Command Palette → **Export Chat**, save directly into this folder. LENS searches here automatically.

If the inputs match the fixture pattern `tc###-log.md` + `tc###-probe-report.md` from `artifacts/testing/fixtures/lens-test-fixtures/`, apply Fixture Audit Mode (defined in the skill) — `chat-*.json` is not required.

**Step 2 — Run the audit.**

Follow the Audit Intake Sequence from the skill exactly:
1. Verify required inputs are present.
2. Cross-check model and date consistency (standard audits only — skipped in Fixture Audit Mode).
3. Detect `extensionVersion` and select the result-retrieval strategy (standard audits only).
4. Read `artifacts/testing/test-plan.md` as the independent expectation source.
5. Check PROBE report frontmatter for `run_type` and `chat_log` fields — determine degradation mode (P1 / P2 / P3).
6. Read the PROBE report **last**.
7. Execute the four-way comparison for each TC-### in scope.
8. Detect behavioral violation patterns across the full session.
9. Produce the audit report.

Do not read the PROBE report before forming independent observations from the chat log.

**Step 3 — Determine the output filename.**

List `artifacts/testing/reports/` and find the highest existing sequence number for files matching `lens-audit-{run_type}-{model}_{YYYY-MM-DD}-*.md` on today's date, then increment by 1. If none exist, use `01`. The output file is:

`artifacts/testing/reports/lens-audit-{run_type}-{model}_{YYYY-MM-DD}-{seq}.md`

Derive `{run_type}` and `{model}` from the PROBE report's `run_type` and `model` frontmatter fields.

**Step 4 — Produce the audit report.**

Write the full audit report to the filename determined in Step 3, using the format defined in the skill:
- Session-Level Anomaly Summary
- Per-TC-### sections with five-column comparison tables and verdict citations
- Violation Log
- Report Truthfulness Summary (P1 mode only)

Every verdict must include a parenthetical citation. A verdict without a citation is invalid.
