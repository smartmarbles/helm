# Output Standards

- **Format:** GitHub-Flavored Markdown unless the brief specifies otherwise.
- **File placement:** Write to the spec folder named in the task brief. If no spec folder is named (standalone documentation task), write to `artifacts/docs/`.
- **Length:** As long as necessary, as short as possible. Respect the reader's time. A 600-line doc that could be 300 is a failure.
- **Pinned versions:** Document header or code-sample line-1 comment. Flag claims likely to drift with `> **Version Note:** ...`.
- **Full imports:** Always. Import paths and module names vary between libraries and must never be assumed.
- **Unstable APIs:** Explicitly noted with `> **Experimental:** ...` or `> **Unstable API:** ...`.
