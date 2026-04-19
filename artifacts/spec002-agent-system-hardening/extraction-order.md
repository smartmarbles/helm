# Phase 3 Skill Extraction Order

Per FR-036, Phase 3 extracts agents in a fixed order: **ARTHUR is always first** as the template for the extraction pattern, and the remaining five permanent agents are ranked in **descending order of agent-file line count**. Line counts were measured on **2026-04-18** using a consistent whole-file line count (blank lines and trailing newline included) across all six files.

## Extraction order

| Slot | Agent | File | Line Count | Rationale |
|------|-------|------|-----------:|-----------|
| 1 | ARTHUR | `.github/agents/arthur.agent.md` | 165 | Template per FR-036 |
| 2 | SAGE   | `.github/agents/sage.agent.md`   | 164 | By line count |
| 3 | PROBE  | `.github/agents/probe.agent.md`  | 162 | By line count |
| 4 | QUILL  | `.github/agents/quill.agent.md`  | 136 | By line count |
| 5 | MERLIN | `.github/agents/merlin.agent.md` |  83 | By line count |
| 6 | SCOOP  | `.github/agents/scoop.agent.md`  |  80 | By line count |

**Tiebreaker rule (not triggered).** If two agents were to share an identical line count, they would be ordered alphabetically by agent name, and the tie would be called out explicitly in the Rationale column. No ties occurred in this measurement.

**Scope.** Temps (including SPLICE and any archived temporary agents under `.github/agents/temps/`) are out of scope for Phase 3 and are intentionally excluded from this ranking.

## Next action

Dispatch MERLIN for P3-T1 (extract ARTHUR).
