# Quick Reference

- **Eight categories, weights summing to 100.** Cluster weight on observed failure modes.
- **Every weight carries a one-sentence rationale.** "Felt important" is not a rationale.
- **Three severities: critical / major / minor.** Assign by consequence, not effort.
- **Critical caps overall at 70.** Non-negotiable.
- **`unclassified` is the runner's escape hatch.** The rubric author decides whether to extend the taxonomy.
- **`expected`, `actual`, `evidence` are all required and all concrete.**
- **Model tag is canonical, typed from the rubric's list.** Untagged run = invalid.
- **Three verification layers: self-ID probe, behavioural fingerprint, user-UI confirm.** No single layer is sufficient.
- **Inconclusive ≠ mismatch.** Document and proceed; do not flag.
- **Adding a model tag ships with its fingerprint row in the same version bump.**
- **Bump minor version for any contract change.** Append a one-line changelog entry.
- **Re-balance weights only from cross-phase evidence.** Never from a single run.
