<p align="center">
  <img src="assets/helm_logo3b.png" alt="Helm Logo orchestration core" width="300" />
  <br/>
  <span style="font-size:1.25em;"><i>Build, compose and run intelligent workflows across agents</i></span>
</p>

# Helm

**Extensible agent orchestration engine for VS Code Copilot.**

## What is Helm?

Helm transforms VS Code Copilot from a single monolithic AI into a coordinated team of specialized agents. It's a framework of agent definition files (`.agent.md`) and orchestration rules that implement hierarchical, generative multi-agent orchestration — where tasks are routed to the right specialist, executed in structured phases, and new agents are created on demand when no existing role fits.

Each agent has a defined identity, expertise, constraints, and communication style. ARTHUR, the chief orchestrator, dispatches work, enforces delegation protocols, and ensures research happens before planning, and planning before execution. The result is structured, repeatable AI-assisted development with clear accountability at every step.

Helm is not a library or runtime. It's a set of conventions and agent definitions that run entirely within VS Code's Copilot agent infrastructure.

> **Theme:** The default team uses an Arthurian theme — ARTHUR, MERLIN, SCOOP, SAGE, QUILL. These are just names. You can rename any agent to fit your team's personality by editing their `.agent.md` file and the roster.

## The Core Team

| Agent | Role | Tagline |
|-------|------|---------|
| **ARTHUR** | Chief Orchestrator | *"The conductor who never plays an instrument."* |
| **MERLIN** | HR Director | *"Every team deserves its architect."* |
| **SCOOP** | Senior Researcher | *"The truth is in the details others skip."* |
| **SAGE** | Strategic Planner | *"A good plan makes implementation feel inevitable."* |
| **QUILL** | Technical Documentation Writer | *"Clear docs are the shortest distance between a developer and a working feature."* |
| **PROBE** | Test Runner | *"X/Y passed. Z failures."* |
| **QUIZ** | Clarification & Readiness Agent | *"Ask less. Classify first. Converge fast."* |

**ARTHUR** never produces deliverables directly — he routes every task to the right agent and tracks progress. **MERLIN** creates new agents by researching role requirements and designing purpose-built personas. **SCOOP** deep-dives into any topic, with every report including a "What Most People Miss" section. **SAGE** builds phased implementation plans with dependency analysis and risk identification. **QUILL** writes developer-facing documentation, running "The Confused Developer Test" on every section. **PROBE** runs automated behavioral tests against the agent system, evaluating pass/fail criteria and producing clean reports. **QUIZ** is an on-demand clarification agent — it classifies prompt unknowns, resolves discoverables from existing project files, and returns a readiness handoff (READY, READY_WITH_ASSUMPTIONS, or NOT_READY) before work begins.

> **Note:** The core team is deliberately infrastructure — orchestration, research, planning, hiring, and documentation. There are no implementation agents in the default roster. When a plan calls for a skillset not covered, ARTHUR engages MERLIN to hire the right specialist (e.g., a TypeScript engineer, a database migration expert, a social publisher) on the fly. This keeps the core team lean and ensures implementation agents are purpose-built for the actual work, not generic.

## How It Works

ARTHUR routes every task through one of three complexity tiers:

### Research Path

For understanding, not building. Triggered by words like "research", "compare", "evaluate", or "investigate".

SCOOP investigates the topic and returns findings directly. If a written document is needed, QUILL is dispatched after SCOOP returns. No spec folder or plan approval required.

### Standard Path

The default for multi-file, multi-agent work.

SAGE creates a plan → **user approves** → ARTHUR hires implementation agents via MERLIN as needed → ARTHUR executes phases, dispatching agents in parallel where possible → completion report.

### Full Path

For new features, migrations, or rewrites. Triggered by "create a spec", "plan this", or similar.

SCOOP researches → SAGE writes a spec → **user approves** → SAGE writes a phased plan → **user approves** → ARTHUR hires implementation agents via MERLIN as needed → ARTHUR executes phases, dispatching agents in parallel where possible → completion report.

The Full Path includes mandatory human approval gates. ARTHUR cannot proceed past spec or plan creation without explicit user confirmation.

## Dynamic Agent Creation

When no existing team member fits a task, ARTHUR identifies the gap and engages MERLIN. MERLIN delegates to SCOOP to research the role requirements, then designs a new agent — complete with persona, skills, constraints, and communication style. The agent is written as a `.agent.md` file and can be permanent (added to the roster) or temporary (archived after task completion).

## Skills and Playbooks

Agents load procedural knowledge in one of two ways:

- **Skills** — reusable instruction sets under `.github/skills/`, loaded by VS Code Copilot via semantic trigger matching on the skill's `description:` field. Reliable on Claude models; triggering is less reliable on OSS models (Qwen3-27B, Gemma 4 31B).
- **Playbooks** — single-agent procedural files under `.github/playbooks/`, loaded explicitly via a mandatory-read block in the owning agent's `.agent.md` file. Reliable on all models.

**Why playbooks instead of more skills?** Skills are always present in the model's context window once created — they add tokens on every invocation whether or not the agent actually needs them for that turn. Playbooks are loaded only when the agent is performing the specific task the playbook covers. For procedures that run infrequently (hiring an agent, archiving a temp, running a test plan), keeping that content out of the always-on context saves significant tokens per conversation. Skills are the right choice when a procedure is genuinely reusable across multiple agents and needs to fire automatically; playbooks are the right choice when a procedure belongs to one agent and is invoked on demand.

The current skill (always-on routing anchor):

| Skill | Used by | Purpose |
|-------|---------|--------|
| `orchestrate-delegation` | ARTHUR | Complexity routing, parallel dispatch, human checkpoints |

The current playbook set (loaded on-demand by the owning agent):

| Playbook | Owned by | Purpose |
|----------|----------|--------|
| `conduct-research` | SCOOP | Investigation planning, source triage, confidence flagging |
| `create-spec` | SAGE | Feature specification authoring |
| `create-plan` | SAGE | Phased implementation planning with dependency annotations |
| `write-technical-docs` | QUILL | Doc-type selection, plan-draft-review loop, code-sample discipline |
| `hire-agent` | MERLIN | Role intake, persona design, agent-file authoring |
| `archive-agent` | MERLIN | Temp agent offboarding and re-archival |
| `skill-creator` | MERLIN | Creating or improving skills |
| `audit-chat-log` | LENS | Chat log auditing and behavioral verification |
| `design-test-rubric` | PROBE | Scorecard weighting, severity taxonomy, violation-log schema |
| `run-test-plan` | PROBE | Test execution, stdout/stderr capture, pass/fail reporting |
| `quizler` | QUIZ | Unknown classification, discoverability override, convergence, stop conditions, register lifecycle |

Every skill must pass `validate_skill.py` (`.github/scripts/`) with zero errors. Run the validator after creating or modifying any skill.

## Key Features

- **Strict role boundaries** — agents have defined responsibilities and constraints, preventing scope creep
- **Human checkpoints** — mandatory approval gates in the Standard and Full Paths before execution begins
- **Parallel dispatch** — independent tasks run simultaneously across multiple agents, with file conflict rules to prevent collisions
- **Generative hiring** — new agents are created on demand when existing roles don't cover a task
- **Session and repo memory** — agents build continuity across conversations through persistent memory files
- **Structured artifacts** — every effort produces artifacts in numbered spec folders (`artifacts/spec###-short-name/`)
- **Research-first protocol** — delegation rules enforce research before planning, and planning before execution

## Developer Workflow

Use these tools to maintain code quality and system health while working within the Helm ecosystem.

### How do I check for errors?

The `get_errors` tool provides a fast, semantics-aware check for compile or lint errors. Use it after every file edit to ensure your changes are valid before proceeding.

**Check specific files:**

```powershell
# Check one or more specific files (absolute paths recommended)
get_errors --filePaths "C:\path\to\file.ts", "C:\path\to\other.ts"
```

**Check the entire workspace:**

```powershell
# Omit filePaths to scan the entire workspace
get_errors
```

> **Note:** Always run `get_errors` after creating or editing any file (including tests) to catch type errors and syntax issues proactively.

## Project Structure

```
AGENTS.md                  # Always-on shared context for all agents
.github/
  copilot-instructions.md  # Bootstrap — loads ARTHUR's identity
  team-roster.md           # Active and archived team members
  agents/                  # Agent definition files
    arthur.agent.md
    merlin.agent.md
    sage.agent.md
    scoop.agent.md
    quill.agent.md
    probe.agent.md
    quiz.agent.md
    temps/                 # Archived temporary agents
  skills/                  # Skills (semantic trigger; one SKILL.md per folder)
    orchestrate-delegation/
  playbooks/               # Playbooks (explicit load; one <name>.md per folder)
    conduct-research/
    create-spec/
    create-plan/
    write-technical-docs/
    hire-agent/
    archive-agent/
    skill-creator/
    audit-chat-log/
    design-test-rubric/
    run-test-plan/
    quizler/
  templates/               # Plan and spec templates
  scripts/                 # Utility scripts
artifacts/                 # Spec folders created per-effort (spec001-*, spec002-*, etc.)
  docs/                    # Standalone documentation (not tied to a spec)
```

> **Note:** Active temporary agents (hired for specific tasks) also appear in `.github/agents/` while they are in use. Check the [team roster](.github/team-roster.md) for the current list.

## Recommended Setup

For best results — especially if you use open-source or smaller orchestrators — **select ARTHUR in the VS Code Copilot chat agent picker** rather than using the default agent.

**Why this matters:**
- When ARTHUR is selected directly, his full `arthur.agent.md` persona is loaded immediately and reliably, even on smaller models.
- When the default agent is used instead, a bootstrap chain fires (`copilot-instructions.md` → read `arthur.agent.md`). This works on capable models, but the chain can be skipped or improperly executed on weaker open-source orchestrators, causing ARTHUR to improvise from partial context rather than load his full instructions.
- Selecting ARTHUR directly removes the persona-conflict risk between the default agent's identity and ARTHUR's instructions.
- Alternatively, addressing ARTHUR by name at the start of your prompt (e.g., "Arthur, let's do X") also triggers the mechanism to load `arthur.agent.md` — this works reliably even on OSS models without changing the agent picker at all.

This is a recommendation, not a requirement. The safety floor in `copilot-instructions.md` (forbidden tools list, delegation mandate, MUST-read pointer) keeps the system functional for users who do not follow this recommendation.

## Getting Started

Helm is a VS Code Copilot agent orchestration system. To use it:

1. **Requirements** — VS Code with GitHub Copilot (Chat) installed and active.

   **Required VS Code settings** (set in your User or Workspace settings JSON):

   | Setting | Value | Why |
   |---------|-------|-----|
   | `chat.subagents.allowInvocationsFromSubagents` | `true` | Enables nested agent calls (e.g., MERLIN → SCOOP). Without this, subagents silently cannot invoke other subagents and fall back to doing the work themselves. |

   Without the required setting, multi-agent routing silently fails. Set it before your first conversation.
2. **Add to workspace** — Copy the `.github` folder into your project workspace. The `.github/copilot-instructions.md` file bootstraps the orchestration system automatically when Copilot reads the workspace.
3. **Start a conversation** — Address ARTHUR (the default) or select a specific agent. Describe your task and ARTHUR routes it through the appropriate complexity path.

**About the safety floor:** `copilot-instructions.md` contains a forbidden-tools list, delegation mandate, identity assertion for ARTHUR, and a MUST-read pointer to `arthur.agent.md`. This floor exists to protect users who don't select ARTHUR directly in the agent picker — it ensures the default agent still behaves approximately as ARTHUR even when the full agent file hasn't loaded. Do not remove it.

For the periodic procedure to keep the safety floor aligned with VS Code's evolving default-agent prompt, run [`.github/prompts/audit-default-agent.prompt.md`](.github/prompts/audit-default-agent.prompt.md).

No build steps, no dependencies, no installation. The agent definitions are the product.

## Model Compatibility

Helm works with both reasoning models (e.g., Claude Opus 4.6, GPT-5.3-Codex) and non-reasoning models (e.g., GPT-4.1). Since Copilot users often have limited premium requests, the orchestration system is designed to function across model tiers without breaking down. Non-reasoning models may require more explicit prompting to output similar quality results.

## Testing

A comprehensive behavioral test plan is included at [`artifacts/testing/test-plan.md`](artifacts/testing/test-plan.md) with 106 test cases across 16 categories. Because Helm has no runtime, tests are conversational — you send a prompt, observe what the agents say and do, and verify the outcome. The plan covers all three execution paths, both approval gates, the dynamic hiring chain, parallel dispatch, constraint enforcement, memory behavior, error recovery, artifact naming, the temporary agent lifecycle, status-query handling, workflow hygiene, and QUIZ agent behavior and artifact readiness.

Of the 106 tests, 43 are marked 🤖 (fully automatable) and can be run by **PROBE**, the test runner agent. An additional 29 are marked 🤖/👤 — PROBE runs the automated criteria while the manual criteria require human observation in VS Code Copilot Chat. Use `@PROBE run all` to execute all automatable tests, or `@PROBE run TC-XXX` for a specific test. PROBE calls target agents as subagents, evaluates responses against pass criteria, checks file system side effects, and cleans up all artifacts. The remaining 34 tests are manual (👤) and require multi-turn interaction or environment changes.

If you want to quickly verify the engine is working without running the full suite, the test plan opens with a **Smoke Test** section — 11 targeted prompts that exercise every critical system: routing, delegation, approval gates, nested agent calls, direct addressing, and constraint enforcement.

## Portability

Helm is built for VS Code Copilot's agent infrastructure, specifically its subagent dispatch system. The orchestration patterns — research before planning, planning before execution, human checkpoints, dynamic hiring — are transferable concepts, but the implementation depends on Copilot's `runSubagent` capability. Other tools (Claude Code, Codex CLI, Gemini) can use the instruction files and agent personas, but multi-agent routing will need to be adapted to each platform's capabilities.

## License

MIT — Copyright (c) 2026 Smartmarbles.com
