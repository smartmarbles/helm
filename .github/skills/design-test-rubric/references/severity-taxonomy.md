# Severity Taxonomy

| Severity | Definition | Sub-score impact |
|----------|------------|------------------|
| **critical** | Violation corrupts output or breaks a hard contract (e.g., the orchestrator produces a deliverable directly; a banned tool fires; a forbidden folder is created). | Category capped at **50** regardless of pass rate. |
| **major** | Violation degrades quality but output is recoverable (e.g., a report missing a required section; a missing checkpoint after a major unit of work). | Category **-10** points per occurrence (floor 0). |
| **minor** | Process-hygiene issue with no user-visible corruption (e.g., redundant grep; unnecessary existence check; misspelled memory slug). | Category **-2** points per occurrence (floor 0). |
