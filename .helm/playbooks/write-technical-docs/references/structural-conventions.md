# Structural Conventions

## Headings

- Top of file: H1 with the document's title and, where useful, version stamp in a subtitle.
- Section headings: H2. Subsections: H3. Rarely H4; if you need H5, the document is too deep — split into linked files.
- Question- or task-oriented phrasing: "How do I …", "Setting up …", "Comparing …", "When to use …". Reference docs can use identifier names as headings (`authenticate()`).

## Code blocks

- Always fenced with the appropriate language tag: ` ```typescript `, ` ```python `, ` ```bash `, etc. Never unfenced.
- Line-1 comment for version context when it matters: `// typescript 5.4, @my/lib 2.1.0`.
- Show full imports or includes. Do not use `// ...existing imports` in samples the reader is meant to run.
- Keep samples focused on one concept. Extract setup into prose before the sample if needed.

## Tables

- Use for structured comparisons, parameter lists, feature matrices, mapping between two things.
- Keep columns narrow enough to render in a 100-column terminal preview — long prose belongs below the table, not inside cells.
- Always commentary after: what does the table tell the reader, and what should they take away.

## Callouts

- `> **Note:** ...` for contextual asides.
- `> **Warning:** ...` for behaviour that breaks silently.
- `> **Version Note:** ...` for claims likely to change.
- `> **Experimental:** ...` or `> **Unstable API:** ...` for pre-stable interfaces.

## Feature gap matrix (comparison docs only)

For comparison docs, use a ✅/❌/🔶 matrix per functional category:

| Feature | Library A | Library B |
|---------|-----------|-----------|
| Zero-config setup | ✅ | ❌ |
| Plugin system | ✅ | 🔶 (community only) |
| Type inference | ✅ | ✅ |

- ✅ = supported, stable.
- ❌ = not supported.
- 🔶 = partial or caveat — always note the caveat in the cell.

Follow every matrix with a verdict paragraph.

## Front-loaded summary

Every document and every section opens with a short statement of what the reader will get. For a full doc:

> This guide shows you how to authenticate requests to the Widget API using OAuth2. You'll end with a working Node.js client that can fetch your account details. Reading time: ~7 minutes.

For a section:

> This section covers the three error types the client can throw. By the end you'll know how to distinguish transient from permanent errors and when to retry.

This earns the reader's attention. If the promise cannot be kept, don't make it.
