# P3-T1 Eval Pass — orchestrate-delegation

**Spec:** spec002-agent-system-hardening
**Task:** P3-T1 (extract ARTHUR process detail into a skill)
**Date:** 2026-04-18
**Mode:** Minimum-viable logical walkthrough (no live run — per task brief, logical walkthrough is acceptable at this phase).

The three evals below are walked through by inspection: does ARTHUR's current agent file (`.github/agents/arthur.agent.md`) combined with the new `orchestrate-delegation` skill produce the behaviour each eval expects? Each eval is verified against the relevant skill section(s).

---

## Eval 1 — Two independent research topics

**Prompt:** *"Research how Next.js middleware compares to Express middleware, and separately look into how Deno's permission model works."*

**Expected ARTHUR behaviour:**
- Classify as **research path** (trigger words "research", "look into").
- Count **two** independent topics.
- Dispatch **two SCOOP agents** in a single batched response.

**Skill support check:**
- Complexity Routing table names "research" as the trigger phrase for the research path ✅
- Delegation Protocol step 1 ("Assess… count the independent tasks or topics") ✅
- Delegation Protocol step 3 ("the same agent type may be dispatched multiple times for separate topics") ✅
- Parallel Dispatch: "Multiple independent research topics → one SCOOP per topic" and "Issue all independent `runSubagent` calls in a single batched response" ✅
- **Worked Example 1** directly illustrates this exact scenario with the DO (two SCOOP dispatches in one batched response) and the DON'T (one combined brief) ✅

**Result:** PASS by inspection. The skill's Complexity Routing + Parallel Dispatch + Example 1 give ARTHUR unambiguous guidance to emit two SCOOP `runSubagent` calls in one response.

---

## Eval 2 — Full path with Spec Checkpoint

**Prompt:** *"Create a spec for a new user-settings page, then implement it."*

**Expected ARTHUR behaviour:**
- Classify as **full path** (trigger: "create a spec").
- Generate spec folder name (e.g., `spec###-user-settings`).
- Dispatch SAGE to write the spec.
- **Verify spec file exists on disk**, summarize to user, **STOP at Spec Checkpoint**.

**Skill support check:**
- Complexity Routing table names "create a spec" as a full-path trigger and names the Spec Checkpoint as a gate ✅
- Artifact Location section gives the short-name generation rules and `spec###-kebab-case` format. The example "Create a dashboard for analytics" → `spec003-analytics-dashboard` matches the shape ARTHUR needs for `spec###-user-settings` ✅
- Human Checkpoints → Spec Checkpoint section prescribes: verify on disk, summarize, ask for explicit approval, STOP ✅
- Worked Example 6 gives a DO/DON'T for exactly this checkpoint behaviour ✅

**Result:** PASS by inspection. The skill prescribes the full flow from classification → folder naming → SAGE dispatch → on-disk verification → summary → explicit-approval stop.

---

## Eval 3 — Simple task, still delegate

**Prompt:** *"Fix the broken link in README.md."*

**Expected ARTHUR behaviour:**
- Recognize the task is trivial but **still delegate** to QUILL.
- Do NOT edit the file directly.
- Do NOT ask the user for permission to delegate.
- Because no spec folder applies, brief QUILL to work on `README.md` directly (standalone doc territory).

**Skill support check:**
- Skill body opens with "ARTHUR never produces deliverables" and the Delegation Protocol makes no carve-out for trivial tasks ✅
- Worked Example 4 ("Simple task, still delegate") directly addresses this exact failure mode with a DO/DON'T pair ✅
- Artifact Location → Standalone Documentation section tells ARTHUR that README/doc work outside a spec effort is standalone; in this case the task is even simpler (single link fix on an existing file) — the principle still holds: delegate, don't do it yourself ✅
- Core principle 1 in the agent file ("Never do the work yourself… delegation is your default action, not a suggestion that requires confirmation") backs the no-permission-ask behaviour — the skill reinforces this with Example 4 ✅

**Result:** PASS by inspection. The skill's Worked Example 4 and the Delegation Protocol together give ARTHUR clear guidance to dispatch QUILL without asking for permission and without shortcutting.

---

## Summary

| Eval | Behaviour tested | Result |
|------|------------------|--------|
| 1 | Research path, parallel dispatch, two topics = two briefs | PASS by inspection |
| 2 | Full path, Spec Checkpoint, on-disk verification, stop for approval | PASS by inspection |
| 3 | Simple task delegation, no self-execution, no permission ask | PASS by inspection |

All three evals map cleanly to identifiable sections of `SKILL.md`. No gaps identified.

## Notes for future live eval runs

If/when a reviewer runs these evals against a live ARTHUR instance:
- Verify dispatches are batched in a single response (eval 1) — look for two tool calls in one assistant turn.
- For eval 2, verify ARTHUR reads the spec file after SAGE returns and explicitly asks for approval before continuing.
- For eval 3, the failure mode to watch for is ARTHUR asking "should I delegate this small fix?" — that's a violation of the "delegation is default, not a suggestion" rule.
