# Helm Memory System — Decision & Implementation Guidance

Audience: engineers operating or extending Helm's Copilot/agent system, and integrators who author agent briefs and skills.

Summary
- Decision: Adopt a hybrid design that follows VS Code Copilot Memory semantics where possible, plus a workspace-local fallback (`.agent-memory/`) when the `memory` tool is unavailable. Prioritize deterministic injection, small user-memory entries, and unique per-agent session checkpoints to avoid races.

Design goals
- Reliable: agents can detect memory availability and degrade gracefully.
- Deterministic: memory injection order and caps keep prompt budgets stable.
- Safe for parallelism: avoid in-place updates that race; prefer unique checkpoint files.
- Discoverable and auditable: clear folder conventions and an audit checklist.

Scope mapping (implementation)
- User scope: `/memories/` — global across workspaces. Use only for short, high-value facts. Keep entries <= 200 lines total (auto-loaded cap).
- Session scope: `/memories/session/` — session-scoped checkpoints and state. Contents are not auto-loaded; agents must `view` explicitly.
- Repo scope: `/memories/repo/` — repo-local facts and configuration. Use for repo-specific policies and fallback pointers.
- Fallback workspace-local: `<workspace>/.agent-memory/{user,session,repo}/` — mirror of the three scopes when the `memory` tool is unavailable.

File organization and naming conventions
- Canonical subfolders:
  - `/memories/helm-team/user/` — short team-wide facts (200-line-friendly).
  - `/memories/session/` — live session checkpoints; file names MUST be unique per-writer: `<agent>-<task-id>-<iso8601>.md`.
  - `/memories/repo/` — stable repo facts: `policy.md`, `memory-fallback.md`, `audit-list.md`.
- Filename pattern rules:
  - Use only ASCII, hyphens, and underscores.
  - Include agent name and a short task id to guarantee uniqueness in parallel runs.

Concurrency, atomicity, and safe update patterns
- Treat `str_replace` and `create` as non-atomic. Avoid parallel writes to the *same* path.
- Safe patterns:
  - Unique-file-per-update: create new files rather than editing an existing checkpoint.
  - Append-by-version: create `<name>-v{NN}.md` to represent successive snapshots.
  - Read-modify-write with advisory backoff (only when strictly necessary) and detection of lost-updates.
- Accept last-writer-wins for non-critical annotations; for authoritative single-source facts use repository PRs or CI-validated updates.

Prompt injection & budget rules
- Injected memory must be deterministic and size-capped. Recommended caps for Helm agents:
  - Per-file cap: 4k characters (approx). If file longer, include a 1-line summary + pointer.
  - Total memory cap per turn: 20k characters.
- Load order: always sort files deterministically (alphabetical by path) before concatenation.
- Truncation policy: when truncation is required, insert a clear `--TRUNCATED--` marker and the original file path.

Agent runtime behavior (must-haves)
- Startup probe: every dispatched agent MUST perform a startup probe:
  1. Try `view /memories/session/`.
  2. If available, set `MEMORY_AVAILABLE=true` and proceed.
  3. If unavailable, set `MEMORY_AVAILABLE=false`, emit a one-time session notification, and use `<workspace>/.agent-memory/` fallback.
- Checkpointing: agents must checkpoint major state changes to `/memories/session/<agent>-<task-id>-<iso8601>.md`.
- Discovery: agents writing a fallback must also write a small repo-scoped pointer `/memories/repo/memory-fallback.md` documenting the fallback path and why it was used.

Security, privacy, and content rules
- Never store secrets or credentials in any `/memories/*` file.
- Minimize PII in user-scoped memory. Prefer hashed identifiers if necessary.
- When storing diagnostic outputs that may include secrets, redact before write.

Operational guidance
- Audit cadence: run a memory audit quarterly. Audit checks:
  - No file exceeds recommended caps without a summary.
  - `/memories/user/` entries are intentional (owner listed in frontmatter).
  - Fallbacks recorded in `/memories/repo/memory-fallback.md`.
- Clean-up policy:
  - Session files: auto-GC after 14 days (align to VS Code behavior).
  - User files: manual review before deletion; prefer archiving to repo-scoped archives.

Developer checklist for adopting this design
- Add startup probe snippet to agent templates.
- Update `AGENTS.md` / agent frontmatter to advertise `memory` dependency (so orchestrator can decide dispatch).
- Add deterministic sort + truncation utilities to prompt-construction libraries.
- Document the fallback path in `artifacts/docs/helm-memory-system.md` and `/memories/repo/memory-fallback.md`.

Examples
- Recommended session filename:

  helm-scan-parse-2026-04-18T15:23:45Z.md

- Sample fallback path in repo memory:

  .agent-memory/session/helm-scan-parse-2026-04-18T15:23:45Z.md

Risks and mitigations
- Risk: Experiment flags can disable `memory` tool unexpectedly → Mitigation: detect and notify; persist pointer to fallback.
- Risk: Cross-workspace leakage via user scope → Mitigation: restrict Helm-specific entries under `/memories/helm-team/` and audit.
- Risk: Silent truncation → Mitigation: explicit `--TRUNCATED--` markers and per-file summaries.

Next steps
- Adopt this doc as the canonical memory design. Implement the startup probe in agent templates (QUILL can author the brief; SAGE/ARTHUR should dispatch code changes).
- Create `/memories/repo/memory-fallback.md` with the chosen fallback path and a brief explanation.

Version note
- v1.0 — Decision recorded 2026-04-18. Revisit after any upstream VS Code memory-tool changes or after Phase 9a validator work.
