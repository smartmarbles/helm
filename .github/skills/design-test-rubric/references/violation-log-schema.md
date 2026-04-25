# Violation Log Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Sequential within the run: `V-001`, `V-002`, … |
| `test_case_id` | string | Test plan ID that surfaced the violation (e.g., `TC-026`). |
| `category` | enum | One of the eight categories defined in the rubric. |
| `rule_violated` | string | Short rule identifier — FR number or plain-English summary (e.g., `FR-052 — orchestrator must delegate, not write`). |
| `expected` | string | What the agent should have done, per the rule. |
| `actual` | string | What the agent actually did — terse, factual, no editorializing. |
| `severity` | enum | `critical` / `major` / `minor` / `unclassified`. |
| `evidence` | string | Pointer to the response excerpt or file path demonstrating the violation. |
