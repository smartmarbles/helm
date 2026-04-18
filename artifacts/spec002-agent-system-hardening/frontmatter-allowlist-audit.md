# Frontmatter Allowlist Audit — spec002 P9a-T2

**Author:** SCOOP
**Date:** 2026-04-18
**Spec:** FR-095 (`artifacts/spec002-agent-system-hardening/spec.md`)
**Consumed by:** P9a-T3 (validator widening)

## Executive Summary

The current validator allowlist in [artifacts/docs/validate_skill.py](artifacts/docs/validate_skill.py) — `{name, description, license, compatibility, metadata, allowed-tools}` — is a verbatim match for the authoritative [agentskills.io specification](https://agentskills.io/specification) and accepts every field currently in use in this repo (only `name` and `description`, in skill-creator). However, the spec has committed to VS Code Copilot-native skills (SR-188, FR-098), and Copilot documents three additional frontmatter fields beyond the open standard: `argument-hint`, `user-invocable`, and `disable-model-invocation`. These must be added to the allowlist to avoid false-positive failures when Copilot-authored skills land.

## Section 1 — Fields in use (existing skills in this repo)

| Field | Type | File | Value (truncated) |
|---|---|---|---|
| `name` | string | [.github/skills/skill-creator/SKILL.md](.github/skills/skill-creator/SKILL.md) | `skill-creator` |
| `description` | string | [.github/skills/skill-creator/SKILL.md](.github/skills/skill-creator/SKILL.md) | `Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, edit, or optimize an existing skill, run evals to test a skill, benchmark skill performance with variance analysis, or optimize a skill's description for better triggering accuracy.` |

**Total skills found:** 1 (`skill-creator`). No other `SKILL.md` files exist under `.github/skills/**`.
**Total distinct fields in use:** 2 (`name`, `description`).

## Section 2 — Current validator allowlist (verbatim)

From the source validator:

```python
ALLOWED_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
```

Required fields enforced separately: `name`, `description`.
Forbidden-field check: any top-level key not in `ALLOWED_FIELDS` raises a hard error.

## Section 3 — Copilot- and standard-documented fields

| Field | Required | Source | Notes |
|---|---|---|---|
| `name` | Yes | [agentskills.io/specification](https://agentskills.io/specification) + [VS Code Copilot docs](https://code.visualstudio.com/docs/copilot/customization/agent-skills#_skillmd-file-format) | Identical definition in both. 1–64 chars, lowercase kebab, must match directory. |
| `description` | Yes | Both sources | Identical. Max 1024 chars, should contain trigger language. |
| `license` | No | agentskills.io | License name or ref to bundled license file. Not mentioned in VS Code docs but spec-allowed. |
| `compatibility` | No | agentskills.io | Max 500 chars. Environment/product constraints. Not mentioned in VS Code docs. |
| `metadata` | No | agentskills.io | Arbitrary key-value map (nested). Not mentioned in VS Code docs. |
| `allowed-tools` | No | agentskills.io (Experimental) | Space-separated pre-approved tools. Marked experimental upstream. |
| `argument-hint` | No | **VS Code Copilot-only** ([docs](https://code.visualstudio.com/docs/copilot/customization/agent-skills#_skillmd-file-format)) | Hint text shown in chat input when skill invoked as slash command. |
| `user-invocable` | No | **VS Code Copilot-only** (same doc) | Boolean, default `true`. Controls `/` menu visibility. |
| `disable-model-invocation` | No | **VS Code Copilot-only** (same doc) | Boolean, default `false`. Set `true` to require manual slash-command invocation. |

**Fields investigated but NOT documented anywhere authoritative for skills:**

| Candidate | Verdict | Evidence |
|---|---|---|
| `model` | **Reject.** Belongs to Copilot **custom agents** (`*.agent.md`), not skills. Not in VS Code's skill frontmatter table nor in agentskills.io. |
| `version` | **Reject at top level.** The agentskills.io spec's canonical example places `version: "1.0"` *inside* `metadata:`, not at the top level. Enforcing it under `metadata` keeps us spec-conformant. |
| `tools` (array) | **Reject.** That is an agent-frontmatter field (per spec002 FR-101, FR-011). The skill equivalent is `allowed-tools` (string, experimental). |
| `applyTo` | **Reject.** That is an `*.instructions.md` field (e.g. the forthcoming `skill.instructions.md` per FR-098), not a `SKILL.md` field. Different file type. |

## Section 4 — Proposed widened allowlist

**Final set (9 fields):**

```python
ALLOWED_FIELDS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
    "argument-hint",
    "user-invocable",
    "disable-model-invocation",
}
```

| Field | Decision | Rationale |
|---|---|---|
| `name` | **Keep** | Required by both agentskills.io and VS Code. Non-negotiable. |
| `description` | **Keep** | Required by both. Non-negotiable. |
| `license` | **Keep** | agentskills.io spec-allowed; harmless; future-proof for shared/redistributable skills. |
| `compatibility` | **Keep** | agentskills.io spec-allowed; lets future skills declare env requirements. |
| `metadata` | **Keep** | agentskills.io spec-allowed; canonical home for `version`, `author`, etc. |
| `allowed-tools` | **Keep** | agentskills.io experimental field. Low cost to retain; future Copilot may honor it. |
| `argument-hint` | **Add** | Documented VS Code Copilot field. Needed the moment any slash-invocable skill is authored. |
| `user-invocable` | **Add** | Documented VS Code Copilot field. Required to hide background-only skills from the `/` menu. |
| `disable-model-invocation` | **Add** | Documented VS Code Copilot field. Required to mark skills as manual-only. |

**Net change vs. current validator:** +3 fields (`argument-hint`, `user-invocable`, `disable-model-invocation`). Zero removals.

**Parser note for P9a-T3:** The existing simple YAML parser flattens nested keys under `metadata:` — it only tracks top-level keys — so sub-keys of `metadata` already pass the allowlist check correctly. No parser change needed for the widening itself. (If a stricter YAML loader is adopted later, ensure `metadata:` remains opaque/nested-allowed.)

## Section 5 — Rejected fields

No fields *currently in use* in this repo are being rejected. Every existing field (`name`, `description` in skill-creator) is on the widened allowlist.

Rejections listed in Section 3 (`model`, top-level `version`, `tools`, `applyTo`) are **candidate** fields that are NOT in use anywhere in this repo and are being pre-emptively excluded from the allowlist with the reasoning recorded there.

## What Most People Miss

1. **The VS Code Copilot docs omit half the open-standard fields.** The Copilot skill-frontmatter table only documents `name`, `description`, `argument-hint`, `user-invocable`, `disable-model-invocation` — it silently drops `license`, `compatibility`, `metadata`, and `allowed-tools` from the agentskills.io spec. If a reviewer does the "audit" by reading only Copilot's docs, they will accidentally *narrow* the allowlist and break spec-conformant skills imported from [anthropics/skills](https://github.com/anthropics/skills) or [github/awesome-copilot](https://github.com/github/awesome-copilot). The correct widening is the **union** of both sources, not Copilot's list alone.

2. **`version` is a trap at the top level.** Multiple authoring LLMs default to emitting `version: "1.0"` as a top-level field (common in other YAML metadata files: npm, cargo, pyproject). The agentskills.io canonical example puts it under `metadata:`. If the validator accepts top-level `version`, you'll entrench the wrong convention; if it rejects it, the error message should tell authors to move it under `metadata`. Consider adding a targeted hint for this case in P9a-T3's validator messages.

3. **`allowed-tools` is a string, not an array.** The agentskills.io spec is explicit: it's a *space-separated string* (`"Bash(git:*) Bash(jq:*) Read"`). Agent frontmatter uses `tools:` as a YAML array. These are not interchangeable, and a validator that only checks "is this key allowed?" won't catch a YAML-list-shaped `allowed-tools`. Type validation for this field is worth a follow-up ticket but is out of scope for FR-095.

4. **`disable-model-invocation: true` + `user-invocable: false` silently disables the skill.** The Copilot docs list this combo in their truth table as "Disabled skills". A skill with both set is syntactically valid and will pass any reasonable allowlist, but it is effectively dead code. Worth a validator **warning** (not error) in P9a-T3 so authors don't ship inert skills. Out of scope for the allowlist itself, but P9a-T3 is the right place to add it.

5. **The validator's `SKIP_DIRS = {"skill-creator"}` means skill-creator is never validated in `--all` mode.** This is the only skill in the repo today. Until more skills exist, the validator runs effectively never on production data, and allowlist regressions won't be caught by CI. P9a-T3 or a later task should reconsider whether skill-creator should be skipped or whether it should be the first skill that must pass.

## Recommendations

1. **P9a-T3 (coder):** Apply the exact 9-field `ALLOWED_FIELDS` set from Section 4 to the relocated validator at `.github/scripts/validate_skill.py` (per FR-092 location). No parser changes required.
2. **P9a-T3 (coder, suggested enhancement, optional):** When rejecting a forbidden field, emit a targeted hint for `version` → "move under `metadata:`" and for `model`/`tools` → "this is an agent-frontmatter field, not a skill field." Low effort, high authoring-ergonomics payoff.
3. **Follow-up ticket (out of scope for FR-095):** Add a warning when `user-invocable: false` AND `disable-model-invocation: true` co-occur (skill is inert).
4. **Follow-up ticket (out of scope):** Reconsider `SKIP_DIRS = {"skill-creator"}` — at least run the validator on skill-creator in a non-strict mode so it catches its own regressions.

---

**Sources cited:**
- agentskills.io specification: https://agentskills.io/specification
- VS Code Copilot Agent Skills docs: https://code.visualstudio.com/docs/copilot/customization/agent-skills
- Current validator: [artifacts/docs/validate_skill.py](artifacts/docs/validate_skill.py)
- Only existing skill: [.github/skills/skill-creator/SKILL.md](.github/skills/skill-creator/SKILL.md)
