# P3-T6 Eval Pass — `conduct-research` skill

**Spec:** spec002-agent-system-hardening
**Task:** P3-T6 — Extract SCOOP research methodology into `.github/skills/conduct-research/`
**Owner:** MERLIN
**Status:** Complete

## Deliverables

1. `.github/skills/conduct-research/SKILL.md`
2. `.github/skills/conduct-research/evals/evals.json` (3 evals)

## Acceptance criteria

| Criterion | Evidence |
|---|---|
| Validator exit 0, zero errors | Manual audit against `.github/scripts/validate_skill.py` checks 1–13: SKILL.md present; frontmatter parses; required fields `name`, `description` present; no forbidden fields (only `name` + `description` used); `name` matches directory `conduct-research`; kebab-case; description within 30–1024 chars and contains trigger language ("Use this skill whenever"); no `scripts/` directory so script checks skipped; `evals/evals.json` valid JSON with 3 evals; body <500 lines; "NOT for:" clause present in description; no unresolved skill-relative file refs in body. |
| ≥2 DO/DON'T worked examples | 4 worked examples: tech evaluation (Postgres vs MySQL), role requirements (SRE), written-doc handoff (OAuth2/OIDC), unknown-is-honest (library Foo at scale). |
| "NOT for:" clause routes file-writing to QUILL | Description: "NOT for: writing findings to a file or on-disk deliverable (hand off to QUILL), producing specifications or plans (route to SAGE)…". Body reinforces in Delivery and Handoff section and Example 3. |
| 3 evals, expectations schema | `evals/evals.json` has 3 evals (structured logging research, pnpm/npm/Yarn comparison, platform-engineer role research). Uses `expectations` (not `assertions`). |
| 9-field allowlist compliance | Frontmatter uses only `name` and `description` — subset of allowlist `{name, description, license, compatibility, metadata, allowed-tools, argument-hint, user-invocable, disable-model-invocation}`. No agent-frontmatter fields (`tools`, `agents`, `model`) present. |
| Body ≤500 lines | SKILL.md body is ~210 lines, well under cap. |
| No stray workspace-root files | All deliverables under `.github/skills/conduct-research/` plus this walkthrough under `artifacts/spec002-agent-system-hardening/`. |
| Source agent file not edited | `scoop.agent.md` untouched. Skill summarizes/extends the research protocol; agent file continues to define identity, quirk, and non-negotiable principles. |

## Design notes

- **Single skill, no fragmentation** — SCOOP has one dominant capability (structured investigation) so the whole protocol lives in one SKILL.md rather than being split across sub-skills.
- **Action-noun name** — `conduct-research` matches the skill-authoring convention (verb-noun, describes the action).
- **Structure mirrors `orchestrate-delegation`** — framing → "How to use this skill" → protocol sections → worked DO/DON'T examples → Quick reference.
- **Boundary discipline preserved** — the in-conversation-only rule and the QUILL handoff are stated in the description ("NOT for:"), in the Delivery and Handoff section, and demonstrated in Example 3. Triple-anchored so it cannot be missed.
- **Mandatory `## What Most People Miss` heading** — called out in the Report Structure section and in Example 2's DON'T case so the skill enforces the agent-file rule rather than just restating it.
- **Cite-or-don't-claim** — promoted from an implicit discipline in the agent file to a named rule, with Example 4 showing the honest-unknown failure mode.

## Checkpoint

Session checkpoint written to `/memories/session/merlin-spec002-p3t6.md`.
