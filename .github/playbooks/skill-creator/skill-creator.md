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
| **Path** | `.github/skills/<name>/SKILL.md` | `.github/playbooks/<name>/<name>.md` |

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
4. Does the skill need test cases? Skills with objectively verifiable outputs (file transforms, data extraction, code generation, fixed workflow steps) benefit from them. Skills with subjective outputs (writing style, tone) usually do not. Suggest an appropriate default but let the user decide.

### Interview and Research

Ask questions about edge cases, input/output formats, example files, success criteria, and dependencies. Wait to write test prompts until this is settled.

Check available MCPs — if useful for research, use them. Come prepared with context to reduce burden on the user.

### Write the SKILL.md

Based on the user interview, fill in these components:

- **name**: Kebab-case skill identifier
- **description**: When to trigger and what it does. This is the primary triggering mechanism — include both what the skill does AND specific contexts for when to use it. All "when to use" info goes here, not in the body. Make the description substantive and specific; vague descriptions fail to trigger. See Description Optimization below.
- **tools**: List of VS Code Copilot tools the skill needs (e.g., `[read, edit, agent]`)
- **NOT for:** clause — always include a brief list of things this skill should NOT be used for. Required by `validate_skill.py` — omitting it will produce a warning.

### Skill Writing Guide

#### Anatomy of a Skill

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description, tools required)
│   └── Markdown instructions
└── Bundled Resources (optional)
    ├── scripts/    — Executable code for deterministic/repetitive tasks
    ├── references/ — Docs loaded into context as needed
    └── assets/     — Files used in output (templates, icons)
```

Do not create an `evals/` directory. Behavioral test cases belong in the test plan (`artifacts/testing/test-plan.md`) — PROBE's territory.

#### Progressive Disclosure

Skills use a three-level loading system:
1. **Metadata** (name + description) — Always in context (~100 words)
2. **SKILL.md body** — In context whenever the skill triggers (<500 lines ideal)
3. **Bundled resources** — Loaded as needed (no hard limit)

Key patterns:
- Keep SKILL.md under 500 lines. If approaching the limit, add a layer of hierarchy with clear pointers to reference files.
- Reference bundled files clearly from SKILL.md with guidance on when to read them.
- For large reference files (>300 lines), include a table of contents.

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

After writing the skill, test it before finalizing:

1. Formulate 2-3 realistic prompts — the kind a real user would actually type.
2. Share them with the user: "Here are a few test cases I'd like to try. Do these look right, or do you want to add more?"
3. Run each prompt in VS Code Copilot with the skill available and evaluate the output qualitatively.
4. If outputs are wrong or incomplete, revise the skill and re-run.

Keep going until:
- The user says they are happy
- All test cases produce correct output
- You are not making meaningful progress

---

## Post-Creation Validation

After writing the skill, run `validate_skill.py` to catch structural problems:

```bash
python .github/scripts/validate_skill.py .github/skills/<skill-name>/
```

Fix any errors (E-prefixed) before finalizing. Warnings (W-prefixed) are advisory — review and address where practical.

Common checks the script enforces:
- `name` is kebab-case
- `description` field is present and has trigger language
- "NOT for:" clause is present in the description
- SKILL.md body is under 500 lines
- All file references from SKILL.md point to files that exist

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
