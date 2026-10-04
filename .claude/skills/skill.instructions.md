---
applyTo: ".claude/skills/**"
---

# Skill Contract

Rules governing how skills are authored, structured, and validated in this project.

## Skill-Creator Modes

The `skill-creator` playbook operates in two distinct modes:

- **Automatic/reference mode** — Used during MERLIN hiring workflows. Read `.helm/playbooks/skill-creator/skill-creator.md` for structural guidance (frontmatter schema, directory layout, eval format) while drafting a new skill. Do NOT invoke the interactive iteration workflow (no subagent runs, no manual test loop).
- **Interactive iteration mode** — User-invoked only. The full manual testing loop: formulate test prompts, run in VS Code Copilot, evaluate qualitatively, refine and re-run. Available when the user explicitly asks to refine or test a skill. NEVER triggered automatically during agent hiring.

## Description Quality

Descriptions must be under **1024 characters**, keyword-rich, and written for discovery. Write in third person: describe the skill's function and the specific tasks or contexts that should trigger it. Do not write from the author's first-person perspective, address the reader in second person, or use only a topic label.

**DO:**
- State what the skill does and when it should be invoked, using concrete task contexts and trigger terms.
- Include a `NOT for:` clause listing explicit negative scope
- Name the owning agent and list trigger phrases that activate the skill
- **Single-quote the `description` value** whenever it contains a colon-plus-space (`: `), a quoted phrase, or any other YAML-special character. Wrap the entire value in single quotes (`description: '...'`) and double any literal single quote inside it (`'` → `''`). This is the standard quoting convention for every skill authored in this repo — apply it regardless of description length.

**DON'T:**
- Write generic descriptions without agent or trigger context
- Omit the `NOT for:` clause
- Exceed 1024 characters
- Leave a `description` unquoted if writing it out forces a colon-plus-space, embedded quotes, or other YAML-special character into the value — an unquoted long description is exactly the situation the single-quoting convention above exists to prevent. Reword or shorten instead of leaving invalid/ambiguous YAML in place.

## Skill Frontmatter

Use the Agent Skills Spec schema for `SKILL.md` files. Do not add unsupported bespoke top-level keys such as `tools`; `validate_skill.py` rejects them. The specification permits `allowed-tools`, but Helm policy prohibits both `allowed-tools` and `permissions` in every skill (FR-055), and permits tool restriction to be relied upon only in a Devin agent profile (FR-056). Agent-wrapper frontmatter is a separate, host-specific schema; wrapper fields do not belong in skill frontmatter.

**Good example** — `orchestrate-delegation`: names ARTHUR, lists trigger phrases ("standard path", "full path"), has `NOT for:` clause with four exclusions, and single-quotes its `description` value.

**Bad example** — *"A skill for doing research"*: no agent name, no triggers, no negative scope.

## Script Dual-Mode Requirement

Scripts in `scripts/` must work both as CLI tools AND be importable:
- Every `.py` file in `scripts/` must have an `if __name__ == "__main__":` guard.
- **Exempt:** Library files (`__init__.py`, `utils.py`, `helpers.py`) — no CLI entry point required.

## Body Size Limit

`SKILL.md` body must be under **500 lines**. If the skill needs more detail, link to files in a `references/` subdirectory rather than expanding the body.

## Validation

> Post-creation validation with `validate_skill.py` is mandatory. For standard skills, a skill task is not complete until the validator exits with zero errors and zero warnings. Third-party skills (with a root `LICENSE` or `LICENSE.txt`) and skills in `SKIP_DIRS` retain their informational-warning-only pass behavior. Skipping validation is a workflow violation regardless of time pressure or task complexity. ARTHUR must confirm validation was executed and passed before accepting the task as complete.

**How to validate:**

```
python .github/scripts/validate_skill.py .claude/skills/<skill-name>
python .github/scripts/validate_skill.py .claude/skills/ --all
```

## Manual Skill Additions

Skills added by the user (not via MERLIN hiring) still require MERLIN review and `validate_skill.py` validation before they are considered complete. Route manual skill additions through MERLIN to ensure the validation contract is met.
