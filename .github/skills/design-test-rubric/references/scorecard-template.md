# Scorecard Template

Every run produces a markdown artifact matching this shape. The rubric owns the template; runners fill in values.

```markdown
---
<YAML metadata per Run Tagging Conventions>
---

# PROBE Scorecard — <model> — <run_date>

## Overall
- **Overall score**: NN / 100
- **Critical violations**: N
- **Total violations**: N

## Category Sub-scores

| Category | Weight | Sub-score | Notes |
|----------|-------:|----------:|-------|
| ... eight rows, one per rubric category ... |

## Test Results

| TC ID | Result | Category | Violations |
|-------|--------|----------|------------|
| TC-001 | PASS | Delegation | — |
| TC-026 | FAIL | Delegation | V-001 (critical) |

## Violation Log

| ID | TC | Category | Rule | Expected | Actual | Severity | Evidence |
|----|----|----------|------|----------|--------|----------|----------|

## Verification
- Layer 1: <probe prompt / exact response / verdict>
- Layer 2: <fingerprint observations / verdict>
- Layer 3: <user-confirm timestamp / reported model>

## Reproduction
- Test corpus: artifacts/spec001-helm-test-plan/test-plan.md
- Test cases run: TC-XXX, TC-YYY, ...
- Rubric: <path to rubric artifact> v<version>
- Model: <model tag>
```

> **Rule:** The scorecard template is fixed per rubric version. Runners do not add, remove, or rename sections. If a section needs to change, it is a rubric revision — bump the minor version and update every scorecard artifact going forward.
