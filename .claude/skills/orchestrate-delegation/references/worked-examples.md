# Orchestrate-Delegation: Worked Examples

Six DO/DON'T pairs illustrating the most common protocol violations and correct behaviours, plus short-name generation examples.

---

## Example 1 — Multiple research topics

**DO:**

> User: "Research how Next.js middleware compares to Express middleware, and separately look into how Deno's permission model works."
>
> ARTHUR: Two independent research topics → two SCOOP dispatches in a single batched response.
>
> ```
> runSubagent(SCOOP, brief: "Compare Next.js middleware vs Express middleware...")
> runSubagent(SCOOP, brief: "Investigate Deno's permission model...")
> ```

**DON'T:**

> ARTHUR: "I'll send SCOOP one brief covering both topics to save a turn."
>
> Wrong. Independent topics get independent briefs. One SCOOP per topic. They run in parallel, not as a combined research dump.

---

## Example 2 — Narration without dispatch

**DO:**

> ARTHUR response includes both the prose ("Dispatching SAGE now to draft the plan") **and** the `runSubagent` tool call, in the same response.

**DON'T:**

> ARTHUR: "I'm sending SAGE now — I'll report back when the plan is ready."
>
> (no tool call in the response)
>
> Wrong. A delegation that exists only in prose did not happen. Emit the tool call in the same response or do not claim the delegation.

---

## Example 3 — Explicit path request

**DO:**

> User: "Use the full path to add a dark-mode toggle."
>
> ARTHUR: SAGE (with SCOOP research as needed) → spec → Spec Checkpoint → plan → Plan Checkpoint → phased execution. Full path end-to-end, even though a dark-mode toggle could plausibly fit the standard path.

**DON'T:**

> ARTHUR: "Dark mode is small — I'll run standard path to save time."
>
> Wrong. The user named the path. Explicit path requests are binding. Never downgrade.

---

## Example 4 — Simple task, still delegate

**DO:**

> User: "Fix the broken link in `README.md`."
>
> ARTHUR: dispatches QUILL with a brief. Even a one-line fix is delegated because ARTHUR never produces deliverables.

**DON'T:**

> ARTHUR: "It's one link, I'll just edit it myself."
>
> Wrong. Core principle violated. Every deliverable goes through an agent. "Too simple to delegate" is not a valid exception.

---

## Example 5 — Parallel vs sequential

**DO:**

> A plan phase annotates T1 (edit `auth.ts`), T2 (edit `billing.ts`), T3 (edit `README.md`) as parallel. No shared files. ARTHUR dispatches all three in one batched response.

**DON'T:**

> ARTHUR dispatches T1, waits for it to finish, dispatches T2, waits, dispatches T3.
>
> Wrong. Independent tasks with no file overlap belong in a single batched dispatch. Sequential dispatch of parallel work wastes wall-clock time.

---

## Example 6 — Spec Checkpoint skip

**DO:**

> SAGE returns: "Spec written to `artifacts/spec007-foo/spec.md`." ARTHUR reads the file, confirms it exists, summarizes the key points to the user, and asks: "Do you approve this spec? I'll proceed to plan generation once you confirm."

**DON'T:**

> ARTHUR: "SAGE finished the spec, moving on to the plan."
>
> Wrong. The Spec Checkpoint is a hard stop. No proceeding without explicit user approval. No exceptions.

---

## Short-name examples

The following examples illustrate how ARTHUR generates spec folder short names from user requests (rules stay in SKILL.md body):

- "I want to add user authentication" → `spec001-user-auth`
- "Implement OAuth2 integration" → `spec002-oauth2-api-integration`
- "Create a dashboard for analytics" → `spec003-analytics-dashboard`
- "Fix payment processing timeout bug" → `spec004-fix-payment-timeout`
