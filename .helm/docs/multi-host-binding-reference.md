# Multi-Host Instruction-Binding Reference

> **Note:** This is the canonical multi-host instruction-binding reference for Helm. It is shipped
> to every project that bootstraps Helm, living at `.helm/docs/multi-host-binding-reference.md`. It
> documents how Helm's capability vocabulary binds to each supported host's concrete tool
> identifiers, and the Appendix table below is read at runtime by
> `.github/scripts/check_wrapper_drift.py` to validate per-host agent wrapper consistency — treat
> it as load-bearing data, not decoration.

## 1. Decision Summary

Helm's instruction layer is restructured so that **one authored source per agent, operating rule,
and playbook serves four hosts simultaneously** — VS Code Copilot, Claude Code, Devin Desktop, and
Cursor — via:

- a new host-neutral directory, **`.helm/`**, holding every authored source (§ 2);
- one thin per-host wrapper per agent, at each host's own discovery path (§ 3);
- a single binding mechanism across all four hosts — the **instruction pointer** — with a named,
  gated fallback for any host on which it does not work (§ 4);
- a documented, three-behavior model for Devin's `allowed-tools` field, so it is never copied
  between file types without review (§ 5);
- a native `AGENTS.md` binding for Devin and Cursor that needs no `@path`-import workaround (§ 6).

## 2. The `.helm/` Host-Neutral Authored-Source Layout

Helm's authored sources live in a single host-neutral directory, `.helm/`, which no host discovers
or auto-loads. Initial structure:

```
.helm/agents/<name>.md
.helm/playbooks/<name>/<name>.md
```

A file under `.helm/` is the thing a human edits; a file at a host discovery path is the thing a
host loads. Except for the skills exception (see § 2.1), no file plays both roles.

**Inertness.** The authored-source home must be inert to every host: no host may auto-discover,
auto-load, or inject its contents. `.agents/` was explicitly rejected as the authored-source home
because it is an *active* discovery path on two in-scope hosts (`.agents/skills/` on VS Code,
`.agents/agents/` on Devin) and — as a design-input caveat only, since Codex is not an in-scope host
this pass — also Codex's native skills home; using it would make authored sources accidentally
loadable. This inertness must hold empirically; if any host is later found to auto-load `.helm/`, a
fallback pointer format applies instead.

**Naming.** The directory is named `.helm/` — dotted, so it reads as a sibling of the host-owned
`.claude/`, `.devin/`, `.cursor/`, and `.github/` directories rather than as part of the consuming
project's own source tree. An undotted top-level `helm/` was rejected because Helm is deployed as an
overlay into other repositories (see `/memories/repo/helm-deployment-model.md`), and `helm/` is the
conventional location for Kubernetes Helm charts — a likely collision in exactly the kind of
repository Helm targets. Because a residual collision risk remains, overlay installation must
support renaming the directory, and the drift check must fail on any pointer still referring to the
old name.

### 2.1 Skills are the one exception

Skills are excluded from this model and remain authored in place at `.claude/skills/**/SKILL.md` —
not moved into `.helm/`, and given no wrapper. Three independent reasons: skills already have
exactly one home discoverable by every in-scope host, so there is no cross-host duplication for a
neutral source to eliminate; a skill's `description` must sit in the discovered `SKILL.md` because
semantic matching reads it there, so the discovered file can never be a pure pointer; and skills
already implement progressive disclosure natively (frontmatter always in context, body loaded on
demand), so a pointer body would add a third load hop to a mechanism that already does the job.
Playbooks, by contrast, move to `.helm/playbooks/` and get **no wrappers** either — for the opposite
reason: a playbook has no host discovery mechanism at all, so a wrapper would exist solely to point
at another file, with no host requirement behind it.

## 3. The Per-Agent Model: One Authored Source, One Wrapper Per Host

Each of Helm's seven agents (ARTHUR, MERLIN, SCOOP, SAGE, QUILL, QUIZ, FORGE) has:

- exactly **one authored source** — `.helm/agents/<name>.md` — the file a human edits; and
- exactly **one thin wrapper per host discovery path**:
  - `.github/agents/<name>.agent.md` (VS Code Copilot)
  - `.claude/agents/<name>.md` (Claude Code)
  - `.devin/agents/<name>.md` (Devin Desktop)
  - `.cursor/agents/<name>.md` (Cursor)

**Cost, stated plainly.** This scales agent files from 7 authored sources to 7 authored sources
plus 4 wrappers each — 28 wrapper files across four hosts — but each added file is a few lines of
frontmatter and one pointer. In exchange, the single largest unverified risk this model addresses
(whether one `.claude/agents/` file could carry both a VS Code and a Claude Code frontmatter
vocabulary at once, and what VS Code would do with unrecognized keys) stops being load-bearing,
because no file is ever asked to satisfy two schemas simultaneously.

**Frontmatter ceiling.** Each wrapper carries **only that host's native frontmatter vocabulary** —
never a second host's fields, never the union of two. `name` and `description` are present in
every wrapper, derived from the authored source, and are the **only** hand-visible duplication
permitted for agents; a drift check covers them regardless of which binding mechanism (pointer or
generated-body fallback) a given host uses.

**Provenance note.** The shipped state covers four wrapper homes: VS Code, Claude Code, Devin
Desktop, and Cursor.

## 4. The Instruction-Pointer Mechanism and Its Fallback

**The binding mechanism is the instruction pointer, on all four in-scope hosts.** A wrapper's body
carries only a pointer to its authored source, and that pointer must reuse the **Mandatory-Read
Template defined in `AGENTS.md` § "Mandatory-Read Template"** verbatim in structure, substituting
only the authored-source path. Freshly authored pointer sentences are non-compliant — the template
is established, proven wording. Concretely, every one of the 28 agent wrappers carries the same
body shape:

```
> **MANDATORY READ — `.helm/agents/<name>.md`**
>
> Before performing this task, you MUST read `.helm/agents/<name>.md` in full. This is not
> optional. Do not improvise from memory. If the file cannot be loaded, STOP and report the
> failure — do not proceed without it. Failure to load is a protocol violation.
```

(Confirmed present, verbatim in structure, in the live [.github/agents/arthur.agent.md](../../.github/agents/arthur.agent.md),
[.claude/agents/arthur.md](../../.claude/agents/arthur.md), [.devin/agents/arthur.md](../../.devin/agents/arthur.md), and
[.cursor/agents/arthur.md](../../.cursor/agents/arthur.md) wrapper files as of 2026-09-24.)

**The fallback is per-host, not a co-equal alternative.** Where a host cannot reference an external
file and content duplication is mechanically unavoidable, the duplicate must instead be *generated*
from the authored source, marked as generated and non-editable, and covered by a drift check that
fails when it diverges. This fallback applies only to a host on which the instruction pointer is
demonstrably not followed, applied per-host, never pre-emptively, and never repo-wide. The
drift-check obligation applies unconditionally to (a) any host that takes the fallback and (b) the
`name`/`description` duplication, which this demotion does not affect.

## 5. Devin's `allowed-tools` Three-Behavior Split

`allowed-tools` semantics must be documented wherever wrappers are authored, because the field has
**three distinct behaviors on Devin**, and the documentation must name all three so they are never
copied between file types without review:

1. **Restrictive** — on a Devin **agent profile**. This is the one surface where `allowed-tools` is
   genuinely restrictive, and the one surface where Helm emits it.
2. **Advisory only** — on a **skill**. The vendor states explicitly that unlisted tools remain
   available and go through normal permission checks. Helm's own policy (not conformance) is to
   emit no `allowed-tools` and no `permissions` block in any `SKILL.md` at all — partly *because*
   the field buys nothing there.
3. **Silently ignored** — when a skill runs as a subagent (`subagent:` or `agent:`).

The advisory and ignored cases must never be described as restrictions. Cursor's tool-restriction
model is a different, host-specific mechanism (the coarse `readonly` frontmatter flag plus
`preToolUse`/`subagentStart` hooks) and must not be assumed to match Devin's three-behavior split.
(Codex's own model — `sandbox_mode`/`mcp_servers` scoping, full-inherit-by-default, no allow/deny
list — is likewise distinct; cited as design input only, since Codex is not an in-scope host this
pass.)

**The published Devin `allowed-tools` ceiling** is exactly five identifiers plus MCP patterns:
`read`, `edit`, `grep`, `glob`, `exec` (plus `mcp__*` where needed). `write` must **not** appear in
any wrapper until confirmed accepted — `edit` covers both write and edit intent, which is why the
capability vocabulary defines a single `edit-file` verb rather than separate create/modify verbs.
Live wrappers scope down from this ceiling to each agent's actual role rather than defaulting to
the full ceiling — e.g. ARTHUR's Devin wrapper grants only `[read, grep, glob]` (no `edit`/`exec`,
matching ARTHUR's orchestrator-only role), while FORGE's grants the full
`[read, edit, grep, glob, exec]` (matching FORGE's implementation role). This per-agent scoping is
the standing rule for every Devin wrapper, not an ARTHUR-only artifact.

## 6. The Devin/Cursor `AGENTS.md`-Native Binding

The Devin binding must **not** rely on `@path` import expansion (no import syntax is published for
Devin). Devin instead binds through the repo-root `AGENTS.md` — a natively supported rule filename
— and, where scoping is needed, `.devin/rules/*.md` with `trigger` frontmatter.

**Cursor needs no comparable workaround at all**: it reads repo-root `AGENTS.md` natively, so the
`CLAUDE.md`/marker-block mechanism is irrelevant to it and no additional binding artifact is
required for Cursor.

(Codex reads `AGENTS.md` natively too, per `codex-cursor-capability-research.md` — cited as
design-input corroboration only; Codex ships no binding artifact because it is not an in-scope host
this pass.)

**Open caveat:** neither default is a hard guarantee — Devin's `agents_standard` flag can be
disabled at project, user, or enterprise scope (default-on, not unconditional), and whether Cursor
exposes any AGENTS.md-disable setting at all remains unconfirmed either way.

---

## Appendix: Capability Vocabulary & Binding Reference

The capability vocabulary and its per-host bindings live in exactly one place — this appendix. No
second copy of this mapping may exist anywhere else in the repository; wrapper frontmatter is
derived *from* this table, never a parallel record of it (this reference and per-host wrapper
frontmatter are the only content exempted from the "no host tool identifiers in shared content"
rule — nowhere else).

Every binding cell holds either a **published identifier with its source**, or the literal marker
**`unverified`**, or the literal marker **`unavailable`** — never an inferred, guessed, or
vendor-analogous name. `unavailable` is a verified negative that shared content must design around;
`unverified` is an open fact awaiting evidence and does not block shared prose (only wrapper
frontmatter).

| Verb | VS Code Copilot | Claude Code | Devin Desktop | Cursor |
|---|---|---|---|---|
| `read-file` | `read` — observed in live wrapper frontmatter (`tools:` array) in [.github/agents/arthur.agent.md](../../.github/agents/arthur.agent.md), [.github/agents/forge.agent.md](../../.github/agents/forge.agent.md), [.github/agents/scoop.agent.md](../../.github/agents/scoop.agent.md); wrapper-load evidence via an alternate method, 2026-09-24 | `Read` — code.claude.com/docs/en/sub-agents, verified 2026-09-23 | `read` — published ceiling; confirmed in [.devin/agents/arthur.md](../../.devin/agents/arthur.md) | `Read(pathOrGlob)` — codex-cursor-capability-research.md, verified 2026-09-22 |
| `edit-file` | `edit` — observed in [.github/agents/forge.agent.md](../../.github/agents/forge.agent.md) `tools:` array, 2026-09-24 | `Write` + `Edit` — code.claude.com/docs/en/sub-agents, verified 2026-09-23 (two identifiers cover Helm's single `edit-file` verb; the single-verb rationale does not force a single Claude identifier) | `edit` — published ceiling; confirmed in [.devin/agents/forge.md](../../.devin/agents/forge.md) | `Write(pathOrGlob)` — codex-cursor-capability-research.md, verified 2026-09-22 |
| `find-files` | `unverified` — **ambiguous, flagged, not resolved by wrapper-load evidence.** `search` is observed in live wrapper grants, but the same identifier is also the best-evidenced binding for `search-content` below, and no separate glob-only identifier is observed in any live wrapper. Recording `search` here would risk a guessed one-to-one mapping the governing spec forbids | `Glob` — code.claude.com/docs/en/sub-agents, verified 2026-09-23 | `glob` — published ceiling | folded into `Read`'s glob support — no separate identifier (codex-cursor-capability-research.md, verified 2026-09-22) |
| `search-content` | `search` — observed in [.github/agents/forge.agent.md](../../.github/agents/forge.agent.md), [.github/agents/scoop.agent.md](../../.github/agents/scoop.agent.md) `tools:` arrays, 2026-09-24 (see `find-files` ambiguity note) | `Grep` — verified 2026-09-23 | `grep` — published ceiling | `Grep` — codex-cursor-capability-research.md, verified 2026-09-22 |
| `run-command` | `execute` — observed in [.github/agents/forge.agent.md](../../.github/agents/forge.agent.md) `tools:` array, 2026-09-24 | `Bash` — verified 2026-09-23 | `exec` — published ceiling | `Shell(commandBase)` — codex-cursor-capability-research.md, verified 2026-09-22 |
| `fetch-url` | `web` — observed in [.github/agents/scoop.agent.md](../../.github/agents/scoop.agent.md) `tools:` array, 2026-09-24 | `unverified` — not addressed by the Claude Code tool identifiers consulted this session | `unverified` — no `allowed-tools` identifier published; Devin's `Fetch()` is a permissions **scope matcher**, not an `allowed-tools` identifier, and must not be used as one (spec § Capability Vocabulary) | `WebFetch(domainOrPattern)` — codex-cursor-capability-research.md, verified 2026-09-22 |
| `invoke-subagent` | `agent` — observed in [.github/agents/arthur.agent.md](../../.github/agents/arthur.agent.md) `tools:` array, 2026-09-24 | `Agent` — code.claude.com/docs/en/sub-agents, verified 2026-09-23 | `unverified` — no published `allowed-tools` identifier; subagent dispatch is enforced via the agent-profile mechanism itself, not a listed tool | `Task` — codex-cursor-capability-research.md, verified 2026-09-22 |
| `access-working-store` | `vscode/memory` — observed in [.github/agents/arthur.agent.md](../../.github/agents/arthur.agent.md), [.github/agents/scoop.agent.md](../../.github/agents/scoop.agent.md) `tools:` arrays, 2026-09-24 | `unverified` — not addressed this session | `unavailable` — no cross-session memory for the Devin Local agent | `unverified` — no dedicated cross-session memory feature is documented at all |
| `ask-user` | `#vscode/askQuestions` — published, documented **unavailable to subagents** (Host Capability Matrix, verified 2026-09-20); corroborated by wrapper-load observation — no live wrapper grants it, consistent with the governing spec | absent/`unavailable` — confirmed absent this session; underlying identifier `unverified` | `ask_user_question` — published, **"always withheld from subagents"** (Host Capability Matrix, verified 2026-09-20) | no identifier documented at all; subagents inherit the parent's full tool surface with no denial carve-out (Host Capability Matrix) — **forbidden by uniform Helm policy regardless**, not inferred from host behavior |
| `track-tasks` | `#todos` — published, documented **unavailable to subagents** (Host Capability Matrix, verified 2026-09-20); corroborated by wrapper-load observation: `todo` observed in [.github/agents/arthur.agent.md](../../.github/agents/arthur.agent.md), [.github/agents/scoop.agent.md](../../.github/agents/scoop.agent.md) | `TodoWrite` — code.claude.com/docs/en/sub-agents, verified 2026-09-23 | `unverified` — not addressed by the host-expansion research | `unverified` — not addressed by the host-expansion research |

**Ambiguity flagged (not silently resolved):** the `find-files` row above is the one cell in this
table where wrapper-load evidence is insufficient to populate a VS Code identifier without
guessing. `search` is the only candidate observed in any live wrapper, but it is equally the
best-evidenced candidate for `search-content`, and nothing in the live wrapper files or in VS
Code's published documentation distinguishes a glob/path-pattern search from a content search under
that one alias. This is recorded as `unverified` rather than resolved by inference; closing it
requires either VS Code's own published tool reference or a live wrapper that grants a visibly
distinct file-pattern identifier.

**Cursor discrepancy flagged.** Cursor's bindings are easy to mischaracterize as leaving "most
vocabulary items unverified/unavailable pending manual testing" — and that does describe Cursor's
**wrapper mechanism** correctly: the Cursor wrapper frontmatter itself carries only `name`,
`description`, `model`, `readonly`, `is_background` (confirmed in
[.cursor/agents/arthur.md](../../.cursor/agents/arthur.md) and [.cursor/agents/forge.md](../../.cursor/agents/forge.md)), a
coarse boolean rather than a per-verb tool grant. It does **not** describe the state of this
*binding reference*: the Capability Vocabulary table above already carries seven of ten Cursor
cells as sourced, published identifiers from `codex-cursor-capability-research.md` (verified
2026-09-22). Only `access-working-store`, `ask-user`, and `track-tasks` are genuinely
`unverified`/undenied for Cursor. This appendix follows that sourced data over the looser
shorthand characterization; flagged here so the discrepancy is visible rather than silently
adjudicated.
