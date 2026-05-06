# Helm Design Principles

> **Audience:** ARTHUR, SAGE, MERLIN, and contributors. Loaded on demand. Consult this document before changing structure, adding always-on context, or introducing new rules.

## 1. Purpose

Helm is a markdown-defined multi-agent orchestration system that drops into VS Code Copilot. It is a production-ready foundation for shipping real work with a small team of specialist agents — not a testing harness. Testing capabilities live as a separate overlay project that layers onto Helm without changing its core.

## 2. Target environment

- **Primary platform:** VS Code Copilot with `runSubagent` available and `chat.subagents.allowInvocationsFromSubagents` enabled.
- **Target model tiers:** Helm runs on both reasoning-tier models (Sonnet 4.x, GPT-5, Opus) **and** non-reasoning / OSS / smaller-context tiers (GPT-4.1, GPT-4.1-mini, Qwen 2.5/3.5, Llama 3.1, Gemini Flash).
- **Binding constraint:** the non-reasoning tier sets the design ceiling. A change that helps reasoning models but degrades OSS-tier performance is wrong for Helm.

## 3. Design principles

1. **Per-agent dispatch stays narrow.** Each agent is small, single-purpose, with a frontmatter-restricted tool surface — narrow dispatch keeps attention on the task.
2. **Always-on context stays small.** [AGENTS.md](../../AGENTS.md), [copilot-instructions.md](../copilot-instructions.md), the active agent file, and skill descriptions load on every dispatch; skill bodies and reference files load on demand — every always-on byte taxes every dispatch.
3. **One source of truth per concept.** Each rule has one canonical home. Other files may reference or briefly summarize the rule; the canonical home is the only place it is fully stated and the only place it is changed — duplicated full statements drift and contradict.
4. **Mechanical enforcement beats prose enforcement.** Tool restrictions, validators, and platform-level gating enforce mechanically; prose that duplicates a mechanical rule is deleted. Prose self-monitoring rules (instructions asking the agent to evaluate its own behavior mid-task) degrade fastest on the target tier and are removed in favor of mechanical or post-hoc verification.
5. **Active voice, present tense, named subject, unambiguous force.** State whether a rule is mandatory ("ARTHUR dispatches one agent per task"), permitted ("ARTHUR may dispatch in parallel when phases are independent"), or forbidden ("ARTHUR does not write files"). Passive voice and hedged force ("should consider", "might want to") obscure intent and degrade reliability on the target tier. State rules positively when possible; when a negative is unavoidable, pair it with the positive alternative ("Do NOT do X. Y instead.").
6. **Hiring produces narrow specialists on demand.** New agents are born small with focused tool surfaces — adding capability does not bloat existing files.
7. **Skills load on trigger; references load on explicit step.** Smaller models trigger skills by description match and read references named in active-voice imperative steps. Skills and references have different reliability profiles and stay separated as authoring mechanisms.
8. **Reference files are single-purpose.** One file equals one job, read in one step — models do not reliably navigate within reference files.
9. **Skills respect the agentskills.io 500-line ceiling.** When a skill body approaches the limit, content extracts to references or splits into a narrower skill — the ceiling is the platform contract, not a Helm preference.
10. **Subtraction before addition.** Cuts to bloat ship before new patterns; patterns from professional frameworks earn entry only after the simplified baseline shows they remain necessary — added structure must justify its weight against an already-lean baseline.
11. **Markdown is the runtime.** Helm has no executor; every rule is a prompt-attention bet — designs that depend on the model perfectly attending to long prose are brittle, so push enforcement to mechanical mechanisms wherever possible.
12. **No functional regression.** Concision is a means, not an end — if shrinking compromises capability, expand the conversation, not the file.
13. **Measure quantitative targets; gate on functional outcomes.** Numerical targets (line counts, token counts, percentages) inform direction; they do not gate completion. The gate is "no functional regression on tested behavior" — when hitting a target compromises capability, expand the conversation, not the file.

## 4. How to be concise without regressing

- Choose the shortest format that conveys the rule unambiguously to a non-reasoning model. That may be a one-line imperative, a 3-row table, a numbered checklist, or a short paragraph — pick per content, not per file.
- Move heavy detail (long procedures, worked examples, doc-type tables, hiring SOPs) to single-purpose reference files invoked at the exact step that needs them.
- Split skills approaching the 500-line cap into either (a) skill plus references or (b) two narrower skills.
- Apply principle #5 to every rule. State force unambiguously; state rules positively when possible.

## 5. What lives where

| Content | Home |
|---|---|
| Universal cross-agent rules (memory scopes, artifact conventions, session protocol, file-link format, output discipline, the orchestration core) | [AGENTS.md](../../AGENTS.md) |
| Default-agent / Copilot-platform-specific behavior only | [.github/copilot-instructions.md](../copilot-instructions.md) |
| Per-agent role, persona, tool surface | `.github/agents/<agent>.agent.md` |
| Reusable procedures triggered by description match | `.github/skills/<skill>/SKILL.md` |
| Heavy procedural detail invoked at one step | `.github/skills/<skill>/references/<topic>.md` |
| Cross-cutting design rationale (this document) | `.github/docs/<topic>.md` |
| Project-scoped artifacts (specs, plans, research) | `artifacts/spec###-name/` |

## 6. Decision discipline

Revisit this document when any of the following occurs:

- A new content type appears and its home is unclear.
- A proposal adds a new always-on file or expands always-on context.
- A new rule requires the model to self-monitor its own behavior.
- A proposal adds prose enforcement of something frontmatter or a validator could enforce mechanically.

## 7. Source context

This document synthesizes findings from:

- [artifacts/docs/multi-model-analysis-synthesis.md](../../artifacts/docs/multi-model-analysis-synthesis.md)
- [artifacts/docs/helm-orchestration-architectural-review.md](../../artifacts/docs/helm-orchestration-architectural-review.md)
- [artifacts/docs/orchestration-framework-comparison.md](../../artifacts/docs/orchestration-framework-comparison.md)
