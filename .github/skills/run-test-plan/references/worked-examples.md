# Worked Examples

## Example 1 — Stream capture on a CLI smoke test

**DO:**

> Task: run the P9a-T4 validator smoke test (`python .github\scripts\validate_skill.py .github\skills\skill-creator --json`).
>
> PROBE creates two temp files, runs `Start-Process -NoNewWindow -Wait -PassThru -RedirectStandardOutput $out -RedirectStandardError $err`, reads each file with `Get-Content -Raw`, records exit code, stdout, and stderr as three separate fields in the log, then deletes both temp files.
>
> Result: stdout contains the JSON; stderr is empty; exit code 0. Each stream logged separately.

**DON'T:**

> PROBE runs `python ... 2>&1 | Tee-Object log.txt` and pastes the merged output as "combined output" into the log.
>
> Wrong. Merging loses the stdout/stderr distinction that downstream assertions depend on. Raw byte redirection to separate temp files is required.

---

## Example 2 — File-system assertion for a "no artifact created" criterion

**DO:**

> Task: TC-052 — "Research path creates no artifact folder."
>
> PROBE lists `artifacts/` and records the snapshot. Dispatches ARTHUR with the research prompt. Re-lists `artifacts/`. Diff is empty → criterion PASS. Records `actual: no new entries under artifacts/` with the pre- and post-listing line counts as evidence.

**DON'T:**

> PROBE dispatches ARTHUR, sees "research complete" in the response, and records PASS without re-listing `artifacts/`.
>
> Wrong. The pass criterion is a file-system assertion, not a response-content check. Skipping the post-test listing means the criterion was never actually verified. Always diff.

---

## Example 3 — Violation recorded with unclassified severity

**DO:**

> TC-035 expects SAGE to refuse TypeScript code. SAGE returns pseudo-code in a fenced block labelled `pseudo`. The rubric defines "produces code" for `.ts/.js/.py` fences; "pseudo" is not in the rubric.
>
> PROBE records:
> ```
> test_id: TC-035
> criterion: SAGE does not produce code
> expected: no code fences
> actual: fenced block with info string "pseudo" containing algorithmic prose; 14 lines
> severity: unclassified
> category: scope-discipline
> evidence: response lines 42-56 in log
> ```
> Flags it in the report for user decision.

**DON'T:**

> PROBE decides "pseudo-code is basically code" and records `severity: major` without a rubric rule.
>
> Wrong. Severity is a rubric call. PROBE observes; the rubric judges. Invented severity pollutes the scorecard.

---

## Example 4 — Cleanup via git

**DON'T:**

> After a hiring test that created a temp agent file and a new spec folder, PROBE runs `git checkout .` to "restore everything at once".
>
> Wrong. `git checkout` reverts ALL uncommitted changes, including any in-progress work that predates the test. The user loses legitimate edits. Always delete specific files by path, verify against the pre-test snapshot.

**DO:**

> PROBE deletes `.github/agents/<new-temp>.agent.md` by exact path, deletes `artifacts/spec099-<test-slug>/` recursively, calls the `memory` tool `delete` on the specific memory keys the test wrote, then re-lists each target directory to confirm an empty diff.
