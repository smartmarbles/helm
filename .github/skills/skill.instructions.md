---
applyTo: ".github/skills/**"
---

# Skill Contract

Rules governing how skills are authored, structured, and validated in this project.

## Skill-Creator Modes (FR-082)

The `skill-creator` skill operates in two distinct modes:

- **Automatic/reference mode** — Used during MERLIN hiring workflows. Read `skill-creator/SKILL.md` for structural guidance (frontmatter schema, directory layout, eval format) while drafting a new skill. Do NOT invoke the interactive iteration workflow (no subagent runs, no HTML viewer, no eval loop).
- **Interactive iteration mode** — User-invoked only. The full eval loop: with-skill/baseline subagent runs, HTML viewer via `generate_review.py`, feedback collection, multi-iteration refinement. Available when the user explicitly asks to refine or test a skill. NEVER triggered automatically during agent hiring.

## Description Quality

Descriptions must be under **1024 characters**, keyword-rich, and written for discovery.

**DO:**
- Use agent-specific trigger language: *"Use this skill whenever MERLIN is asked to hire…"*
- Include a `NOT for:` clause listing explicit negative scope
- Name the owning agent and list trigger phrases that activate the skill

**DON'T:**
- Write generic descriptions without agent or trigger context
- Omit the `NOT for:` clause
- Exceed 1024 characters

**Good example** — `orchestrate-delegation`: names ARTHUR, lists trigger phrases ("standard path", "full path"), has `NOT for:` clause with four exclusions.

**Bad example** — *"A skill for doing research"*: no agent name, no triggers, no negative scope.

## Script Dual-Mode Requirement

Scripts in `scripts/` must work both as CLI tools AND be importable:
- Every `.py` file in `scripts/` must have an `if __name__ == "__main__":` guard.
- **Exempt:** Library files (`__init__.py`, `utils.py`, `helpers.py`) — no CLI entry point required.

## Body Size Limit

`SKILL.md` body must be under **500 lines**. If the skill needs more detail, link to files in a `references/` subdirectory rather than expanding the body.

## Validation (FR-080a)

> Post-creation validation with `validate_skill.py` is mandatory. A skill task is not complete until the validator exits with zero errors. Skipping this step is a workflow violation regardless of time pressure or task complexity. ARTHUR must confirm validation was executed and passed before accepting the task as complete.

**How to validate:**

```
python .github/scripts/validate_skill.py .github/skills/<skill-name>
python .github/scripts/validate_skill.py .github/skills/ --all
```

## Manual Skill Additions

Skills added by the user (not via MERLIN hiring) still require MERLIN review and `validate_skill.py` validation before they are considered complete. Route manual skill additions through MERLIN to ensure the validation contract is met.
