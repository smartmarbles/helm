## Memory Scope Convention

Copilot's memory tool exposes three scopes, distinguished by path prefix. Agents choose the correct scope based on **content portability** — who should see this, and for how long. The extension routes by prefix automatically; no config file or namespace subfolder is involved.

| Scope | Path prefix | Write here when… |
|-------|-------------|------------------|
| **Session** | `/memories/session/` | Working state for the current task — checkpoints, handoff notes, in-progress outlines. Cleared or superseded when the task ends. |
| **Repo** | `/memories/repo/` | Durable project knowledge — conventions, architectural decisions, verified facts about this codebase. Survives across sessions within this workspace. |
| **User** | `/memories/` | Content that genuinely crosses projects — personal preferences, language-agnostic lessons, cross-workspace tooling notes. Rare. |

### Default: write durable project knowledge to `/memories/repo/`

When in doubt between user and repo scope, choose **repo**. Project-specific insights belong with the project.

### Warning: user scope leaks across workspaces

> **Warning:** The first 200 lines of every file under `/memories/` are loaded into **every Copilot session in every workspace** on this machine. A note written here during one project will appear in the context of every unrelated project thereafter.

Do not write to `/memories/` unless the content is explicitly cross-project. Project-specific names, paths, decisions, and conventions must go to `/memories/repo/` instead. A misfiled user-scope note is effectively a context leak into every future session.

### Non-decisions (stated so they are not re-litigated)

- **No `helm.config.json`** — scope selection is a writing discipline, not a configured namespace.
- **No project subfolders under `/memories/`** (e.g., no `/memories/helm-team/`) — the three built-in scopes are sufficient. The path prefix *is* the namespace.
- **No tooling enforcement** — agents choose the scope correctly by convention. Misfiled notes are corrected by moving the file, not by validation machinery.
