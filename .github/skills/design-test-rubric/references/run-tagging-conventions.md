# Run Tagging Reference

## YAML Block Template

```yaml
---
run_id: <slug>-<YYYYMMDD>-<nn>
model: <model-tag>
run_date: YYYY-MM-DD
test_corpus: artifacts/spec001-helm-test-plan/test-plan.md
test_cases_run: [TC-001, TC-003, ...]
rubric_version: 1.0.0
---
```

## Canonical Model Tag Values

Model tags are the comparison axis across phases. Drift in tag values destroys cross-run comparability.

- `gpt-4.1`
- `gpt-5-mini`
- `claude-sonnet-4.6`
- `claude-opus-4.7`

Add new model tags only in the rubric (the `design-test-rubric` skill), never ad-hoc in a run log. New tags bump the rubric's minor version.
