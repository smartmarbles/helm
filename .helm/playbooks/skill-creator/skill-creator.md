# Skill Creator

Playbook for creating new skills, improving existing skills, and optimizing skill descriptions. Owned by MERLIN.

---

## When to use a skill vs. a playbook

Before creating anything, decide which artifact is appropriate:

| | Skill | Playbook |
|---|---|---|
| **Use when** | Procedure is reusable across multiple agents | Procedure belongs to exactly one agent |
| **Loaded by** | VS Code Copilot semantic trigger on `description:` field | Explicit mandatory-read block in agent's `.agent.md` |
| **OSS model reliability** | Unreliable (Qwen3-27B, Gemma 4 31B may not trigger) | Reliable — fires unconditionally |
| **Path** | `.claude/skills/<name>/SKILL.md` | `.helm/playbooks/<name>/<name>.md` |

If the procedure is single-agent only, create a playbook instead and skip this playbook. If genuinely reusable across agents, continue here.

---

## Communicating with the user

Pay attention to context cues to calibrate vocabulary. Users range from first-time terminal openers to senior engineers. In the default case:

- "evaluation" and "benchmark" are borderline but OK
- "JSON" and "assertion" — only use without explanation if the user has already demonstrated they know what these are

It is fine to briefly define terms if you are in doubt.

---

## Creating a skill

### Capture Intent

Start by understanding the user's intent. The current conversation might already contain a workflow to capture (e.g., "turn this into a skill"). If so, extract answers from the conversation history first — tools used, sequence of steps, corrections made, input/output formats observed. The user may need to fill gaps and should confirm before you proceed.

1. What should this skill enable the model to do?
2. When should this skill trigger? (what user phrases or contexts)
3. What is the expected output format?
4. Which representative prompts and expected behaviors should the skill's evals cover? Every skill needs an `evals/evals.json` file with behavioral test cases. Gather cases for the skill's key workflows, including subjective outputs where expectations can be described; plan for at least 3 cases because fewer trigger a validator warning and a standard skill passes only with zero warnings.

5. Before substantial authoring, capture a no-skill baseline:
    - Write 2-3 realistic prompts that expose tasks the model handles poorly or inconsistently without this skill.
    - Note the failure signal or desired behavior for each scenario.
    - Run each prompt without the skill and record how the model actually behaves.
    - Keep prompts and task context stable so later runs can be compared fairly.
    - Reuse these scenarios as core Manual Testing prompts and measure revisions against the recorded baseline.

### Interview and Research

Ask questions about edge cases, input/output formats, example files, success criteria, and dependencies. Wait to write test prompts until this is settled.

Check available MCPs — if useful for research, use them. Come prepared with context to reduce burden on the user.

### Write the SKILL.md

Based on the user interview, fill in these components:

- **name**: Kebab-case skill identifier
- **description**: Describe the skill's function in third person and the specific contexts that should trigger it. This is the primary triggering mechanism; include both what the skill does and when it should be invoked. Keep it substantive and specific. See Description Optimization below.
- **NOT for:** clause — always include a brief list of things this skill should NOT be used for. Required by `validate_skill.py`; omitting it is a hard error.

Use the Agent Skills Spec schema for `SKILL.md` frontmatter. The validator rejects unsupported top-level keys such as `tools`. Although the specification permits `allowed-tools`, Helm policy prohibits both `allowed-tools` and `permissions` in every `SKILL.md` (FR-055); tool restriction may be relied upon only in a Devin agent profile (FR-056). Agent-wrapper frontmatter follows separate, host-specific schemas and must not be copied into a skill.

### Skill Writing Guide

#### Anatomy of a Skill

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name and description required; optional spec fields)
│   └── Markdown instructions
├── evals/ (required)
│   └── evals.json — behavioral test cases
└── Bundled Resources (optional)
    ├── scripts/    — Executable code for deterministic/repetitive tasks
    ├── references/ — Docs loaded into context as needed
    └── assets/     — Files used in output (templates, icons)
```

#### How to document bundled scripts and resources

Point from the skill body to each bundled resource and explain when to use it. For every bundled script:

- State explicitly whether the model should execute it or only read/inspect it as reference.
- Name every parameter and magic constant it expects, including how to provide each value.
- State any defaults and side effects the model needs to account for when invoking it.
- Make failures visible and actionable; do not defer or silently hide errors.
- For fragile or higher-risk operations, validate useful intermediate outputs before proceeding rather than chaining steps blindly.

Include `evals/evals.json` with behavioral test cases for every skill. Missing or empty evals are validator errors; at least one case is required. Fewer than 3 cases triggers `W-FEW-EVALS`; because a standard skill passes validation only with zero errors and zero warnings, 3 or more cases are required for a clean pass. These per-skill behavioral evals are distinct from the broader QA test plan (`artifacts/testing/test-plan.md`); both can coexist and serve different purposes.

#### Progressive Disclosure

Skills use a three-level loading system:
1. **Metadata** (name + description) — Always in context (~100 words)
2. **SKILL.md body** — In context whenever the skill triggers (<500 lines ideal)
3. **Bundled resources** — Loaded as needed (no hard limit)

Key patterns:
- Keep SKILL.md under 500 lines. If approaching the limit, add a layer of hierarchy with clear pointers to reference files.
- Reference bundled files clearly from SKILL.md with guidance on when to read them.
- For large reference files (>100 lines), include a table of contents — models often only read a file's first ~100 lines, so an unflagged missing TOC beyond that point risks silently skipped content.

#### Domain Organization

When a skill supports multiple domains or frameworks, organize by variant:

```
cloud-deploy/
├── SKILL.md (workflow + selection logic)
└── references/
    ├── aws.md
    ├── gcp.md
    └── azure.md
```

The model reads only the relevant reference file.

#### Principle of Lack of Surprise

Skills must not contain malware, exploit code, or any content that could compromise system security. A skill's contents should not surprise the user in their intent if described. Do not create misleading skills or skills designed to facilitate unauthorized access, data exfiltration, or other malicious activities.

#### Writing Patterns

Prefer the imperative form in instructions.

**Defining output formats:**
```markdown
## Report structure
ALWAYS use this exact template:
# [Title]
## Executive summary
## Key findings
## Recommendations
```

**Examples pattern:**
```markdown
## Commit message format
**Example:**
Input: Added user authentication with JWT tokens
Output: feat(auth): implement JWT-based authentication
```

### Writing Style

Explain *why* things are important rather than relying on heavy-handed MUST/NEVER directives. Today's models are smart — good reasoning in the instructions transmits understanding better than rigid commands. Use theory of mind. Write a draft, then read it with fresh eyes before finalizing.

If you find yourself writing ALWAYS or NEVER in all caps, treat it as a signal to reframe: explain the reasoning instead. That approach is more humane, more powerful, and more effective.

---

## Manual Testing

After writing the skill, test it before finalizing. Start with the representative failure scenarios and no-skill baseline captured under Capture Intent:

1. Use the 2-3 baseline scenarios as realistic test prompts; add cases if needed to cover other key workflows.
2. Share them with the user: "Here are a few test cases I'd like to try. Do these look right, or do you want to add more?"
3. Run each prompt with the skill available on every intended model tier, not only the model you happen to be using.
    - Account for the OSS-model caveat above: semantic skill triggering can be unreliable.
    - Verify that the skill activated on each tier instead of assuming a description change guarantees it.
    - Record the model tier and whether activation occurred for each run.
    - If activation failed, distinguish that from a failure to follow the skill's instructions.
4. Observe real or similar tasks in use, and gather team feedback where available.
    - Check whether the model found and followed the right instructions and resources without getting lost.
    - Assess navigation and instruction-following separately from final-answer correctness.
    - Note missed rules, navigation failures, and incomplete outputs, not only whether the final answer looks right.
5. Compare results with the no-skill baseline, revise the minimum guidance needed to address observed failures, and re-run the same scenarios on each intended tier.

Keep going until:
- The user says they are happy
- Test cases produce correct output and the model reliably finds and follows the relevant guidance
- You are not making meaningful progress

---

## Post-Creation Validation

After writing the skill, run `validate_skill.py` to catch structural problems:

```bash
python .github/scripts/validate_skill.py .claude/skills/<skill-name>/
```

Resolve all errors (E-prefixed) and warnings (W-prefixed) before considering a standard skill complete. Third-party skills (with a root `LICENSE` or `LICENSE.txt`) and skills in `SKIP_DIRS` are exempt from the zero-warning pass condition; their warnings remain informational.

Common checks the script enforces:
- `name` is kebab-case
- `description` field is present and has trigger language (any warning must still be resolved for a standard skill to pass)
- "NOT for:" clause is present in the description or body (hard error if missing)
- SKILL.md body is no more than 500 lines (hard error if exceeded)
- All file references from SKILL.md point to files that exist (hard error if unresolved)
- Each `references/*.md` file over 100 lines has a detectable table of contents near the top (hard error if missing)

---

## Improving a Skill

### How to Think About Improvements

1. **Generalize from feedback.** The goal is a skill that works across many different prompts, not just the examples you tested. Avoid overfitting — instead of adding rigid case-specific rules, try different framings or metaphors that handle the general case better.

2. **Keep the prompt lean.** Remove content that is not pulling its weight. If it looks like the skill causes the model to spend time on unproductive steps, cut the instructions driving that behavior.

3. **Explain the why.** Try to understand what the user actually wants and transmit that understanding into the instructions. When you find yourself reaching for ALWAYS or NEVER in all caps, reframe instead: explain the reasoning so the model understands why something matters.

4. **Look for repeated work.** If multiple test runs independently produced the same helper script or multi-step approach, that is a signal the skill should bundle that script in `scripts/`. Write it once and instruct the skill to use it.

---

## Description Optimization

The `description` field in SKILL.md frontmatter is the primary mechanism that determines whether VS Code Copilot invokes a skill. After creating or significantly changing a skill, offer to review the description for triggering quality.

### How Triggering Works

Skill descriptions are matched semantically against the user's request. The important thing: VS Code Copilot only consults a skill for tasks it cannot easily handle on its own. Simple, one-step queries may not trigger a skill even if the description matches, because the model can handle them directly. Complex, multi-step, or specialized queries reliably trigger skills when the description matches.

On OSS models (Qwen3-27B, Gemma 4 31B), semantic triggering is unreliable regardless of description quality. If reliable activation on OSS models is required, a playbook is a better choice.

### Step 1: Generate Trigger Eval Queries

Create 20 eval queries — a mix of should-trigger and should-not-trigger. The queries must be realistic and specific, not abstract. Good queries include context detail: file paths, personal situation, column names, company names, some backstory. Bad queries are vague one-liners.

```
Bad:  "Format this data"
Good: "my boss sent me a Q4_sales_final_FINAL_v2.xlsx and wants me to add a profit
       margin % column. revenue is col C, costs are col D"
```

For **should-trigger** queries (8-10): cover different phrasings of the same intent — some formal, some casual. Include cases where the user does not explicitly name the skill but clearly needs it.

For **should-not-trigger** queries (8-10): focus on near-misses — queries that share keywords with the skill but actually need something different. Obvious negatives ("write a fibonacci function" as a negative for a PDF skill) test nothing. The negative cases should be genuinely tricky.

Share the query set with the user for review and refinement before proceeding.

### Step 2: Manual Evaluation

Run each query in VS Code Copilot and note whether the skill triggered or not. Tally:

- Should-trigger queries that did trigger: ✅
- Should-trigger queries that did NOT trigger: ❌ (description needs to be more specific/substantive)
- Should-not-trigger queries that triggered: ❌ (description is too broad)

### Step 3: Revise the Description

Based on the misses, tighten or broaden the description as needed. Re-run the query set. Repeat until the miss rate is acceptable.

### Step 4: Apply the Result

Update the `description` field in SKILL.md frontmatter. Show the user before/after. Run `validate_skill.py` again to confirm the updated description still passes the trigger-language check.

---

## Adding to the Agent File

After creating the skill and running post-creation validation:

1. Confirm the skill is genuinely reusable across multiple agents. If it turns out to be single-agent only, convert to a playbook instead.
2. Add a `## Skills` section (or entry) to each agent that should use it, listing the skill name, path, and a one-line description.
3. Update the team roster if this is a new skill category.
