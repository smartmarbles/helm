# P3-T3a Eval-Pass Walkthrough — `run-test-plan` skill

Logical walkthrough verifying that each eval prompt, when handled by PROBE loading the `run-test-plan` skill, produces behaviour that matches both the skill's guidance and the source `probe.agent.md` — confined to execution (rubric-design content lives in the parallel `design-test-rubric` skill).

## Eval 1 — `run-p9a-t4-validator-smoke`

**Prompt:** "Run the P9a-T4 validator smoke test … capture stdout and stderr separately as raw byte streams, record the exit code, and append the result to `artifacts/spec002-agent-system-hardening/frontmatter-allowlist-audit.md` …"

**Skill-directed behaviour:**
1. Skill's Stream Capture section requires `Start-Process -NoNewWindow -Wait -PassThru -RedirectStandardOutput $out -RedirectStandardError $err` with two separate temp files.
2. Exit code (`$p.ExitCode`), stdout (`Get-Content $out -Raw`), stderr (`Get-Content $err -Raw`) are recorded as three distinct fields.
3. "Appending to the test-log artifact" rule → fenced `stdout:` and `stderr:` blocks appended under a dated section; empty streams labelled `(empty)`, not omitted.
4. Cleanup Protocol → `Remove-Item $out, $err` and re-list to verify.
5. Report Format → sign off with `X/Y passed. Z failures.`

**Cross-check against `probe.agent.md`:**
- "You execute each test by … Cleaning up … so the workspace is restored" — preserved in Cleanup Protocol and the stream-capture temp-file cleanup.
- "report what IS, not what should be" — empty streams labelled `(empty)` rather than omitted is the concrete manifestation.
- P9a-T4 log capture method in `frontmatter-allowlist-audit.md` line 245 is the exact `Start-Process … -RedirectStandardOutput -RedirectStandardError` pattern the skill codifies.

**Expectations satisfied:** all five (separate redirection, three-field record, log artifact append, temp-file cleanup, tally sign-off).

## Eval 2 — `run-delegation-constraints-against-gpt41`

**Prompt:** "Run category E (delegation/scope constraints) against GPT-4.1: TC-026, TC-027, TC-028, TC-029, TC-032, TC-035, TC-060 …"

**Skill-directed behaviour:**
1. Input Commands table → `run category E` is a valid scope.
2. Execution Protocol step 2 → read each TC from `artifacts/spec001-helm-test-plan/test-plan.md`, not the registry.
3. Steps 3–4 → snapshot `artifacts/`, `.github/agents/`, and the `memory` tool views of `/memories/session/` and `/memories/repo/` per test; dispatch target agent with exact input prompt.
4. Evaluation Rules → delegation, refusal, and structure checks apply. Rule: one failed criterion fails the whole test.
5. Violation Log section → each failure logged with the full seven-field schema. Rule: no invented severity → `unclassified` when rubric has no rule.
6. Cleanup Protocol → delete by specific path; `memory` tool `delete`; NEVER git commands.
7. Report Format → summary table + Failures + Violation Log + Cleanup Status + tally.

**Cross-check against `probe.agent.md`:**
- "You run only tests marked 🤖" and "Always read the specific test case from the test plan before executing it — do not rely on the registry table alone" — preserved in Execution Protocol step 2 and Input Commands.
- "NEVER use `git checkout`, `git restore`, or any git commands for cleanup" — preserved verbatim intent in Cleanup Protocol "Rule: never use git for cleanup".
- "A test passes only if ALL pass criteria are met" — preserved as "Rule: one failed criterion fails the whole test".
- Violation recording with severity tiering is split: PROBE records observations; severity *rules* are rubric territory (design-test-rubric). Skill enforces this via "Rule: no invented severity".

**Expectations satisfied:** all five (plan-read discipline, all-criteria pass rule, violation-log schema, path-specific cleanup, report format).

## Eval 3 — `run-file-assertion-no-artifact-created`

**Prompt:** "Run TC-052 against ARTHUR: the research path must not create an artifact folder …"

**Skill-directed behaviour:**
1. File-System Assertions section → pre-test snapshot of `artifacts/`, post-test listing, diff. PASS iff zero added entries.
2. Rule: report what IS → `actual` field records the listing/diff summary, not "looked fine".
3. Rule: modified-pre-existing-file = contamination → emit `⚠️ CONTAMINATION: [path] was modified by TC-052` and DO NOT revert.
4. Cleanup Protocol → any accidentally-created files are deleted by specific path and verified with a re-list.
5. Rule: stop on cleanup failure → `⚠️ CLEANUP FAILED: [what remains]` halts the run rather than cascading poison into the next test.

**Cross-check against `probe.agent.md`:**
- "Compare against your pre-test snapshot" and "If a test modifies a pre-existing file … report it as contamination … Do NOT attempt to revert it" — preserved verbatim intent in File-System Assertions section.
- "If cleanup fails, report it explicitly" — preserved in Cleanup Protocol "Rule: stop on cleanup failure".
- Delegation-vs-side-effect distinction: this test's pass criterion is a file-system assertion, so the skill's Evaluation Rules specifically require diffing rather than inferring from response text. Worked example 2 dramatizes the failure mode.

**Expectations satisfied:** all five (diff-based assertion, concrete `actual` record, path-specific cleanup with verify, contamination report without revert, stop-on-cleanup-failure).

## Scope-boundary check

All three evals exercise execution mechanics: stream capture, test-plan reads, snapshot/diff assertions, violation recording, scorecard population, cleanup, and report format. None require PROBE to *author* rubric categories, weight them, define severity tiers, or design the scorecard schema — those are the `design-test-rubric` skill's territory and are explicitly listed in this skill's `NOT for:` clause. Rubric-related language in the skill body ("per the rubric", "`unclassified` if the rubric has no rule") is deliberately *consuming* rubric decisions, never producing them.

## Verdict

All three evals produce behaviour that is traceable to both the new `run-test-plan` skill and the source `probe.agent.md`. Execution content was extracted faithfully; rubric-design content was left to the parallel `design-test-rubric` dispatch and is not duplicated here.
