# OpenClaw Pattern Assessment

Five multi-agent orchestration patterns from the OpenClaw project were evaluated for adoption in our VS Code Copilot agent system. Two were rejected as infeasible given host-platform constraints; three were adopted with implementation approaches suited to Copilot's extension model.

## Pattern 1: Runtime Tool Filters per Role

- **OpenClaw approach:** Filter available tools per agent role at runtime, enforcing least-privilege tool access dynamically.
- **VS Code Copilot feasibility:** Not feasible. Copilot does not expose runtime tool-filtering APIs.
- **Decision:** Rejected
- **Reasoning:** The host platform cannot enforce runtime tool restrictions. Mitigated by declaring intended tool access via `tools` arrays in agent frontmatter — a declaration, not enforcement.
- **FR reference:** FR-101

## Pattern 2: Slash-Command Routing

- **OpenClaw approach:** Use slash commands (e.g., `/research`, `/plan`) to route requests to specific agents.
- **VS Code Copilot feasibility:** Not feasible. Copilot does not support custom slash-command registration.
- **Decision:** Rejected
- **Reasoning:** No host-level integration exists for custom slash commands. The `@agent` mention syntax is the supported routing mechanism.
- **FR reference:** FR-102

## Pattern 3: Prompt-Cache Stability

- **OpenClaw approach:** Deterministic ordering of injected context to maximize LLM prompt-cache hit rates.
- **VS Code Copilot feasibility:** Partially feasible. Agent instruction files (AGENTS.md, CLAUDE.md, copilot-instructions.md) are sorted by URI string (confirmed in source code). For other context types — custom agents, skills, `.instructions.md` files — no ordering guarantee exists. Observed alphabetical order on Windows/NTFS is a filesystem artifact, not a platform contract. Skills use priority-tier sorting (workspace → personal → plugin), not filename order.
- **Decision:** Adopted with caveats
- **Reasoning:** Content stability (same files, same content) matters more than injection order for prompt-cache hits. The system achieves stability by keeping files self-contained and avoiding cross-file ordering dependencies. File naming conventions remain useful for human readability but should not be relied upon for cache behavior.
- **FR reference:** FR-103

## Pattern 4: "NOT for:" Clauses in Skill Descriptions

- **OpenClaw approach:** Include negative-scope clauses in capability descriptions to prevent misrouting.
- **VS Code Copilot feasibility:** Feasible and already implemented via FR-032.
- **Decision:** Adopted
- **Reasoning:** Every skill description includes a "NOT for:" clause. Validator flags absence as a warning.
- **FR reference:** FR-104

## Pattern 5: Char-Budgeted Injection

- **OpenClaw approach:** Track and budget character/token cost of injected context to avoid exceeding context windows.
- **VS Code Copilot feasibility:** Feasible. Agent files have a 150-line target (FR-040). Skills have a 500-line body limit.
- **Decision:** Adopted
- **Reasoning:** Line-count targets serve as a practical proxy for token budgeting. Validator enforces limits during authoring.
- **FR reference:** FR-105

## Summary

| Pattern | Decision | FR |
|---|---|---|
| Runtime tool filters per role | Rejected | FR-101 |
| Slash-command routing | Rejected | FR-102 |
| Prompt-cache stability | Adopted (with caveats) | FR-103 |
| "NOT for:" clauses | Adopted | FR-104 |
| Char-budgeted injection | Adopted | FR-105 |
