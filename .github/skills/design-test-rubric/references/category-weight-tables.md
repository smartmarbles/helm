# Category and Weight Tables

## Category Table Shape

Every rubric covers exactly **eight categories** whose weights sum to **100**.

| # | Category | Weight | One-sentence rationale |
|---|----------|-------:|------------------------|

The total row must be present and explicit:

| **Total** | | **100** | |

## Sub-score Calculation

Compute each category sub-score as:

```
sub_score = (tests_passed_in_category / tests_attempted_in_category) × 100
```

Compute the overall score as the weighted sum:

```
overall = Σ (sub_score_i × weight_i) / 100
```

Severity penalties adjust sub-scores before the weighted sum.
