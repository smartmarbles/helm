# Temp Agent Discovery Test & Archive Strategy Decision

**Spec:** spec002-agent-system-hardening | **Tasks:** P7-T1, P7-T2
**Date:** 2026-04-19

---

## P7-T1 — Empirical Discovery Test

### Method

SPLICE was a single-dispatch temp agent created for spec002 P9a-T3. Its agent file was placed at `.github/agents/temps/splice.agent.md` per the archive-on-creation convention for temps.

1. **Observation:** SPLICE did not appear in the VS Code Copilot agents roster injected into system prompts while located in `temps/`.
2. **Action:** The file was moved to `.github/agents/splice.agent.md` (the top-level agents directory).
3. **Result:** SPLICE immediately appeared in the agents list and became invocable via `runSubagent`.

### Result

VS Code Copilot does **not** recurse into subdirectories of `.github/agents/`. Only `.agent.md` files placed directly in `.github/agents/` are discovered and injected into the system prompt.

### Conclusion

The discovery mechanism is flat — subdirectory placement is sufficient to hide an agent from the Copilot runtime. No additional configuration, naming convention, or flag is needed to make an agent undiscoverable.

---

## P7-T2 — Archive Strategy Decision

### Decision: Keep current location convention

| State | Location |
|-------|----------|
| **Active temp** | `.github/agents/<name>.agent.md` |
| **Archived temp** | `.github/agents/temps/<name>.agent.md` |

Moving a temp from `.github/agents/` to `.github/agents/temps/` naturally removes it from VS Code Copilot's discovery scope. No additional mechanism is required.

### FR-071 Satisfaction

FR-071 required that archived temps not be auto-discovered. The empirical test above confirms this is already the case with the current directory structure. **No additional action is needed** — the existing convention satisfies the requirement by design.

### Cross-references

The discovery constraint is documented in:

- **`AGENTS.md`** — Discovery constraint callout in the Team Structure section
- **`hire-agent` skill** — Placement guidance for new temps
- **`archive-agent` skill** — Archive/unarchive move instructions
