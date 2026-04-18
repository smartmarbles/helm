# Spec 003 — Agent File Parser (implementation plan)

## Summary
A TypeScript-based parser and discovery tool for `.agent.md` files that extracts YAML frontmatter, validates it against a maintained schema, and exposes a clean API for tooling (validation, metrics, discovery). This is a greenfield implementation (no existing TS toolchain in repo). Target: Node >=20, ESM, `yaml` + `zod`, vitest for tests.

## Phases

## Phase 1: Foundation — initialize TS tool and core parsing
- Task 1.1: Initialize package & toolchain → Implementer
  Files: artifacts/spec003-agent-file-parsing/package.json, artifacts/spec003-agent-file-parsing/tsconfig.json
- Task 1.2: Implement low-level parsing utilities (split frontmatter robustly, handle CRLF) → Implementer
  Files: artifacts/spec003-agent-file-parsing/src/parse.ts
- Task 1.3: Implement schema + types using `zod` and export inferred TS types → Implementer
  Files: artifacts/spec003-agent-file-parsing/src/schema.ts
- Task 1.4: Add error classes and small helpers (line counts, warnings) → Implementer
  Files: artifacts/spec003-agent-file-parsing/src/errors.ts, artifacts/spec003-agent-file-parsing/src/utils.ts
> PARALLEL: Tasks 1.1 and 1.2 may run concurrently; 1.3 depends on 1.2; 1.4 depends on 1.2
> BLOCKED BY: none

## Phase 2: Discovery, CLI & tests — make it usable
- Task 2.1: Implement discovery (glob `.github/agents/**/*.agent.md`) and `discoverAgents()` → Implementer
  Files: artifacts/spec003-agent-file-parsing/src/discover.ts
  Depends on: Task 1.2, Task 1.3
- Task 2.2: Implement public barrel + exported API (`index.ts`) → Implementer
  Files: artifacts/spec003-agent-file-parsing/src/index.ts
  Depends on: Task 1.3
- Task 2.3: Add tests for parse + schema + discovery using `vitest` and real agent fixtures → Implementer / Test author
  Files: artifacts/spec003-agent-file-parsing/test/parse.test.ts, artifacts/spec003-agent-file-parsing/test/fixtures/*
  Depends on: Task 1.2, Task 1.3, Task 2.1
- Task 2.4: Add a small CLI shim `bin/agent-validate` to run single-file validation and emit JSON → Implementer
  Files: artifacts/spec003-agent-file-parsing/src/cli.ts, artifacts/spec003-agent-file-parsing/package.json (bin)
> PARALLEL: Tasks 2.1 and 2.2 run in parallel; 2.3 runs after 2.1 and 2.2; 2.4 can be done in parallel with 2.3
> BLOCKED BY: Phase 1 (all tasks)

## Phase 3: Integration & packaging — repo hygiene and handoff
- Task 3.1: Place `validate_skill.py` and this parser as sibling scripts under `.github/scripts/` per spec002 alignment → Implementer / Repo maintainer
  Files: .github/scripts/agent-parser/* (copy or symlink from artifacts path)
  Depends on: Phase 2 success
- Task 3.2: Documentation: README.md (usage, API, examples), and short developer guide → QUILL (doc writer) or Implementer
  Files: artifacts/spec003-agent-file-parsing/README.md, artifacts/spec003-agent-file-parsing/USAGE.md
- Task 3.3: Optional: publish as package / prepare for monorepo split → ARTHUR/MERLIN decision
  Files: N/A (release notes, package metadata)
> PARALLEL: Tasks 3.1 and 3.2 can run concurrently; 3.3 is independent business decision
> BLOCKED BY: Phase 2 (all tasks)

## File Assignments (every task lists files above)
- All new source lives under: artifacts/spec003-agent-file-parsing/src/
- Tests and fixtures live under: artifacts/spec003-agent-file-parsing/test/
- Package metadata lives at: artifacts/spec003-agent-file-parsing/package.json
- Final placement for repo consumption: `.github/scripts/agent-parser/` (mirror or move after review)

## Watch Out
- No TS/Node toolchain exists in the repo; bootstrapping package.json and Node target (Node >=20) is required.
- The canonical schema may change as spec002 progresses. Implement "warn on unknown fields" by default; do not fail on unknown frontmatter keys.
- Choose `yaml` (YAML 1.2) over `js-yaml` to avoid legacy boolean coercions.
- Use robust frontmatter splitting anchored to line boundaries and `\r?\n` to handle CRLF on Windows.
- The parser should expose `discoverAgents(root)` not rely on `process.cwd()` to ease testing.
- Keep the parser forgiving: warnings for style issues (name/slug mismatch, missing "Use when:" phrase) rather than hard errors.
- If this will replace `validate_skill.py`, coordinate with the owner of that script before disabling it.

## Open Questions
- OQ-1: What is the primary immediate consumer? (validation CI, spec002 metrics, distribution tooling) — this determines API ergonomics.
- OQ-2: Should unknown frontmatter fields be captured in `ParsedAgent.unknownFields` or merely logged as warnings? (affects schema shape)
- OQ-3: Where should the canonical home be after development: stay under `.github/scripts/agent-parser/` or become a top-level package `packages/agent-parser/`?
- OQ-4: Confirm Node engine target (>=20 recommended) and module system (ESM preferred).

## Next Steps (for implementer)
1. Create the package skeleton (`package.json`, `tsconfig.json`) and install `yaml` + `zod` + `vitest` as dev deps.
2. Implement `parse.ts` to split frontmatter safely and return `ParsedAgent`.
3. Implement `schema.ts` with `zod` and wire validation/warnings.
4. Add unit tests using the existing `.github/agents/*.agent.md` files as golden fixtures.

---

This plan file generated by SAGE. After implementation, save a session checkpoint at `/memories/session/sage-spec003-progress.md` recording completed tasks and file paths.