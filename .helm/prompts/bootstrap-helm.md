---
description: Bootstrap the Helm multi-agent orchestration system into the current workspace by downloading all required files from GitHub, for use across VS Code Copilot, Claude Code, Devin Desktop, and Cursor.
---

> This file is the canonical, sole copy of the `bootstrap-helm` prompt — there is no separate wrapper file pointing to it. It is not auto-discovered by any host's prompt-file picker (VS Code's `#` prompt-file auto-discovery is deliberately not used for it). A new user invokes it by fetching this file directly and attaching or referencing it in a Copilot chat session (e.g. via `#file:` or "Add Context").

# Bootstrap Helm Multi-Agent System

You are bootstrapping the **Helm** multi-agent orchestration system into the current workspace. This bootstrap prompt itself runs inside a VS Code Copilot chat session (reached by fetching this file directly and attaching or referencing it — e.g. via `#file:` or "Add Context" — not through VS Code's prompt-file auto-discovery, which this file does not use), but the files it installs are what let the resulting project be worked on from **any** of Helm's four supported hosts — VS Code Copilot, Claude Code, Devin Desktop, and Cursor — not VS Code alone. You must execute all steps below **in order** using terminal commands. Do NOT use file-creation tools — all files must be created via terminal commands (`curl`, `Invoke-WebRequest`, `mkdir`, etc.).

> **Update Mode:** This same document is followed identically whether this is a first install into a fresh workspace or a later update to a project that has already been bootstrapped before. Nearly every step is naturally idempotent on a repeat run — directory creation, the merge-safe file procedure, plain regular-file overwrites, and validation all behave the same whether or not the target already exists. Exactly two steps are the exceptions and behave differently on a repeat run: **Step 3a** reconciles `.github/team-roster.md` against local and upstream history instead of overwriting it, and **Step 5** already skips re-vendoring `skills-ref` entirely when `VENDOR_INFO.md` already names the current pinned commit. No other step requires special-casing for "is this an update?" **Step 1a** runs identically on every invocation too — it simply resolves to the default `.helm` when nothing has been renamed yet, which is the normal case on a fresh install — so it is not a third install-vs-update exception the way Step 3a and Step 5 are. It exists for an orthogonal reason: so a prior, opt-in rename of `.helm/` (see "Renaming `.helm/`" below) is respected by every later step, independent of whether this run is an install or an update.

---

## File Manifest

This is the **single source of truth** for all files managed by this bootstrap. Every subsequent step references this manifest — no file paths are defined elsewhere. When adding or removing files from Helm, update ONLY this manifest.

> **Note:** `.github/scripts/check_manifest_drift.py` is a maintainer-only tool (it is not part of this bootstrap's own install manifest) that diffs the paths listed in this section against the repo's actual tracked files under Helm's governed directories, failing if any tracked file isn't listed here. Run it after adding files to confirm the manifest stays complete — the same role `check_wrapper_drift.py` plays for rename drift (see "Renaming `.helm/`" below).

**Base URL:** `https://raw.githubusercontent.com/smartmarbles/helm/main/`

### Merge-safe files
These files may already exist with user content. They are wrapped in `<!-- HELM BEGIN -->` / `<!-- HELM END -->` markers (see Step 3).

| Local path | Remote path |
|---|---|
| `AGENTS.md` | `AGENTS.md` |
| `CLAUDE.md` | `CLAUDE.md` |
| `.github/copilot-instructions.md` | `.github/copilot-instructions.md` |

`AGENTS.md` is the shared, host-neutral rules file read directly by Claude Code, Devin Desktop, and Cursor. `CLAUDE.md` is a thin Claude Code entry point that imports `AGENTS.md`. `.github/copilot-instructions.md` is VS Code Copilot's own entry point. All three carry the same merge procedure because a consuming project may already have its own content in any of them.

### Regular files
These files are downloaded directly (overwrite if they exist).

Helm's agents, playbooks, and probes are authored once in a host-neutral home, `.helm/` (see "Renaming `.helm/`" below), and discovered per host through a thin wrapper file that points back at the authored source:

```
.helm/agents/arthur.md
.helm/agents/forge.md
.helm/agents/merlin.md
.helm/agents/quill.md
.helm/agents/quiz.md
.helm/agents/sage.md
.helm/agents/scoop.md
.helm/playbooks/archive-agent/archive-agent.md
.helm/playbooks/conduct-research/conduct-research.md
.helm/playbooks/conduct-research/evals/evals.json
.helm/playbooks/conduct-research/references/quick-reference.md
.helm/playbooks/conduct-research/references/worked-examples.md
.helm/playbooks/create-plan/create-plan.md
.helm/playbooks/create-spec/create-spec.md
.helm/playbooks/hire-agent/hire-agent.md
.helm/playbooks/quizler/quizler.md
.helm/playbooks/skill-creator/skill-creator.md
.helm/playbooks/write-technical-docs/write-technical-docs.md
.helm/playbooks/write-technical-docs/evals/evals.json
.helm/playbooks/write-technical-docs/references/boundaries.md
.helm/playbooks/write-technical-docs/references/doc-type-table.md
.helm/playbooks/write-technical-docs/references/output-standards.md
.helm/playbooks/write-technical-docs/references/quick-reference.md
.helm/playbooks/write-technical-docs/references/structural-conventions.md
.helm/playbooks/write-technical-docs/references/worked-examples.md
.helm/playbooks/write-technical-docs/references/writing-standards.md
.helm/docs/multi-host-binding-reference.md
.helm/PROBE-INERTNESS.md
```

Every agent gets one wrapper file per host — 7 agents × 4 hosts:

```
.github/agents/arthur.agent.md
.github/agents/forge.agent.md
.github/agents/merlin.agent.md
.github/agents/quill.agent.md
.github/agents/quiz.agent.md
.github/agents/sage.agent.md
.github/agents/scoop.agent.md
.claude/agents/arthur.md
.claude/agents/forge.md
.claude/agents/merlin.md
.claude/agents/quill.md
.claude/agents/quiz.md
.claude/agents/sage.md
.claude/agents/scoop.md
.devin/agents/arthur.md
.devin/agents/forge.md
.devin/agents/merlin.md
.devin/agents/quill.md
.devin/agents/quiz.md
.devin/agents/sage.md
.devin/agents/scoop.md
.cursor/agents/arthur.md
.cursor/agents/forge.md
.cursor/agents/merlin.md
.cursor/agents/quill.md
.cursor/agents/quiz.md
.cursor/agents/sage.md
.cursor/agents/scoop.md
```

Skills live in Claude Code's native skills location, which every in-scope host is expected to honor:

```
.claude/skills/skill.instructions.md
.claude/skills/orchestrate-delegation/SKILL.md
.claude/skills/orchestrate-delegation/evals/evals.json
.claude/skills/orchestrate-delegation/references/worked-examples.md
```

Remaining supporting files — team roster, docs, hooks, templates, scripts (including the drift-check tool), and archival placeholders:

```
.github/agents/temps/.gitkeep
.github/docs/helm-design-principles.md
.github/docs/memory-fallback.md
.github/docs/session-protocol.md
.github/hooks/hooks.json
.github/hooks/scripts/hook.py
.github/scripts/check_wrapper_drift.py
.github/scripts/copilot_token_analyzer.py
.github/scripts/token_proxy.py
.github/scripts/validate_skill.py
.github/templates/adr-template.md
.github/templates/definition-entry-template.md
.github/templates/plan-template.md
.github/templates/quiz-handoff-template.md
.github/templates/spec-template.md
artifacts/.gitkeep
artifacts/docs/.gitkeep
```

The hook script (`hook.py`) is a single cross-platform Python 3 file used unchanged on Windows, macOS, and Linux — `hooks.json` selects the right launcher (`python` vs `python3`) per OS, not a different script. `check_wrapper_drift.py` is described in Step 6 and in "Renaming `.helm/`" below rather than repeated here.

### `.github/team-roster.md` (reconciled, not overwritten)

```
.github/team-roster.md
```

Unlike every other path in "Remaining supporting files" above, this file is **not** a plain overwrite. It accumulates real local state over a project's life — agents a consuming project has hired or archived — so a blind re-download on an update run would silently destroy that local history. It is handled by its own step, `## Step 3a: Reconcile team-roster.md`, which runs instead of (not in addition to) Step 4's generic download for this one path.

Step 3a's reconciliation needs no third file. Every row in `.github/team-roster.md` carries a `Source` column tagged either `Helm core` (shipped by Helm's own upstream roster) or `Local hire` (added by this project). Reconciliation reads that column on the current local file and compares it against the freshly-downloaded upstream file — there is no separate snapshot file to fetch, check, or write.

### Vendored package

One additional dependency is not a plain file download — it is pinned to a specific upstream commit and vendored via `git`, not `curl`. See Step 5. Step 5 also generates a local provenance file for that dependency.

```
.github/scripts/vendor/skills-ref/  (pinned upstream commit, see Step 5)
.github/scripts/vendor/skills-ref/VENDOR_INFO.md  (generated locally during Step 5, not cloned from upstream; records the pinned commit, pinned/vendored dates, and license for the vendored copy)
```

---

## Renaming `.helm/`

`.helm/` is Helm's default name for the host-neutral directory holding the authored source of every agent, playbook, and probe. No host reads `.helm/` directly — every host discovers Helm's team only through the per-host wrapper files listed above, each of which points back at a file under `.helm/`.

`## Step 1a: Detect the host-neutral root directory`, below, automatically detects and respects an existing rename on every subsequent bootstrap run — it does not perform a new rename itself. The numbered procedure in this section remains the only way to actually perform one.

If the target project already uses a top-level `.helm/` directory for something else, the installer may rename it to any other name. A rename is only complete when **every** pointer agrees:

1. Rename the directory itself first, before writing or editing any wrapper file.
2. Update every wrapper file's pointer (all 28 agent wrappers, plus any playbook or probe reference inside `AGENTS.md`, `CLAUDE.md`, and `.github/copilot-instructions.md`) to the new name. Partial renames — some pointers on the old name, some on the new one — are not a supported end state.
3. Run `.github/scripts/check_wrapper_drift.py`. It is required to fail with a non-zero exit if it finds even one pointer still naming the old directory. A clean run of this script — not a manual search — is the only accepted signal that a rename is finished.

---

## Step 1: Detect OS

Determine the current operating system and store it for use throughout:

- **Windows** → use PowerShell commands
- **macOS / Linux** → use bash commands

Run a quick detection command (e.g., `uname` on bash, or check `$env:OS` on PowerShell) and remember the result as `OS_NAME`. All subsequent steps provide commands for both OSes — use only the set matching `OS_NAME`.

### Prerequisite: confirm Python is on PATH

`.github/hooks/hooks.json` invokes every hook as a bare `python3 .github/hooks/scripts/hook.py` (bash/macOS/Linux) or `python .github/hooks/scripts/hook.py` (Windows) — there is no venv activation anywhere in that invocation. Helm's hooks therefore require an ambient, PATH-resolvable Python 3 interpreter; a project-local virtual environment would not be found by that bare invocation. This check is only confirming a machine-wide interpreter is reachable — it is not asking you to choose between a venv and a machine install.

If no interpreter is found, **abort the bootstrap now**. Do not continue to Step 2 or any later step. Report the failure to the user and tell them to install Python 3 and ensure it is on `PATH`, then re-run this bootstrap.

### bash (macOS / Linux)

```bash
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 was not found on PATH."
  echo ".github/hooks/hooks.json invokes hooks as a bare 'python3' with no venv activation, so a PATH-resolvable Python 3 interpreter is required."
  echo "Install Python 3 and ensure it is on PATH, then re-run this bootstrap."
  exit 1
fi
echo "Found $(command -v python3) ($(python3 --version))."
```

### PowerShell (Windows)

```powershell
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
  Write-Host "ERROR: python was not found on PATH."
  Write-Host ".github/hooks/hooks.json invokes hooks as a bare 'python' with no venv activation, so a PATH-resolvable Python interpreter is required."
  Write-Host "Install Python 3 and ensure it is on PATH, then re-run this bootstrap."
  exit 1
}
Write-Host "Found $($pythonCmd.Source) ($(python --version))."
```

---

## Step 1a: Detect the host-neutral root directory

### Rationale

`.helm/` can be renamed per the "Renaming `.helm/`" procedure described earlier in this document. If a project already did that, a later bootstrap run must write to the renamed location, not recreate a fresh `.helm/` alongside it. This step detects the current root once, up front, so every later step that writes under `.helm/` uses the right location.

### Detection mechanism

Check whether `.github/agents/arthur.agent.md` exists.

- If it does **not** exist, this is a fresh install — the root is the default `.helm`.
- If it **does** exist, read it and extract the path referenced on its `> **MANDATORY READ — ...**` line (the exact current format is: `` > **MANDATORY READ — `.helm/agents/arthur.md`** `` — a backtick-quoted path ending in `/agents/arthur.md`). Strip the trailing `/agents/arthur.md` suffix from the extracted path to get the root (e.g. `.helm`, or whatever it was renamed to).

### bash (macOS / Linux)

```bash
HELM_ROOT=".helm"
if [ -f ".github/agents/arthur.agent.md" ]; then
  POINTER_LINE=$(grep "MANDATORY READ" ".github/agents/arthur.agent.md" | head -n1)
  POINTER=$(echo "$POINTER_LINE" | grep -o '`[^`]*/agents/arthur\.md`' | tr -d '`')
  if [ -n "$POINTER" ]; then
    HELM_ROOT="${POINTER%/agents/arthur.md}"
  fi
fi
echo "Using host-neutral root: $HELM_ROOT"
```

### PowerShell (Windows)

```powershell
$helmRoot = ".helm"
if (Test-Path ".github/agents/arthur.agent.md") {
  $content = Get-Content -Raw ".github/agents/arthur.agent.md"
  if ($content -match 'MANDATORY READ[^\r\n]*`([^`]*?/agents/arthur\.md)`') {
    $pointer = $Matches[1]
    $helmRoot = $pointer -replace '/agents/arthur\.md$', ''
  }
}
Write-Host "Using host-neutral root: $helmRoot"
```

This step performs detection only — it never renames anything itself and never deletes or recreates any directory. It only determines which root name later steps should write to.

---

## Step 2: Create directories

Extract the parent directory of every file in the manifest (both categories) and create each unique directory. If a directory already exists, skip it silently. Any manifest path with a `.helm/` prefix must use the `HELM_ROOT` / `$helmRoot` value resolved in Step 1a in place of the literal `.helm` segment when deriving its directory — every other prefix is used as-is from the manifest.

**Derivation rule:** For each file path in the manifest, take its parent directory. Deduplicate the list. Create all directories.

### bash (macOS / Linux)

Build the directory list from the manifest file paths above, then run:

```bash
mkdir -p <space-separated list of unique parent directories derived from the manifest>
```

### PowerShell (Windows)

Build the directory list from the manifest file paths above, then run:

```powershell
$dirs = @(<comma-separated quoted list of unique parent directories derived from the manifest>)
foreach ($d in $dirs) {
  New-Item -ItemType Directory -Force -Path $d | Out-Null
}
```

---

## Step 3: Handle merge-safe files

Apply the merge procedure below to each file listed under **Merge-safe files** in the File Manifest.

### Merge procedure (apply for EACH file)

Given a `LOCAL_PATH` and a `REMOTE_URL`:

1. Download the remote content to a temporary file.
2. If `LOCAL_PATH` exists, create a backup copy at `LOCAL_PATH.bak` before making any changes.
3. Check whether `LOCAL_PATH` exists.
   - **Does NOT exist** → Create `LOCAL_PATH` with content: `<!-- HELM BEGIN -->`, then the downloaded content, then `<!-- HELM END -->`.
   - **Exists and contains `<!-- HELM BEGIN -->` marker** → Replace everything from `<!-- HELM BEGIN -->` through `<!-- HELM END -->` (inclusive) with: `<!-- HELM BEGIN -->`, then the downloaded content, then `<!-- HELM END -->`.
   - **Exists but has NO markers** → Append a blank line, then `<!-- HELM BEGIN -->`, the downloaded content, then `<!-- HELM END -->` to the end of the file.
4. Delete the temporary file.

### File 1: `AGENTS.md`

- **Local path:** `AGENTS.md`
- **Remote URL:** `https://raw.githubusercontent.com/smartmarbles/helm/main/AGENTS.md`

### File 2: `.github/copilot-instructions.md`

- **Local path:** `.github/copilot-instructions.md`
- **Remote URL:** `https://raw.githubusercontent.com/smartmarbles/helm/main/.github/copilot-instructions.md`

### File 3: `CLAUDE.md`

- **Local path:** `CLAUDE.md`
- **Remote URL:** `https://raw.githubusercontent.com/smartmarbles/helm/main/CLAUDE.md`

### bash (macOS / Linux)

Run the following function, then call it for both files:

```bash
merge_helm_file() {
  local local_path="$1"
  local remote_url="$2"
  local tmp_file
  tmp_file=$(mktemp)

  curl -fsSL "$remote_url" -o "$tmp_file"

  # Back up existing file before modification
  if [ -f "$local_path" ]; then
    cp "$local_path" "${local_path}.bak"
    echo "BACKUP created: ${local_path}.bak"
  fi

  if [ ! -f "$local_path" ]; then
    # File does not exist — create with markers
    printf '<!-- HELM BEGIN -->\n' > "$local_path"
    cat "$tmp_file" >> "$local_path"
    printf '\n<!-- HELM END -->\n' >> "$local_path"
    echo "CREATED $local_path (with HELM markers)"
  elif grep -q '<!-- HELM BEGIN -->' "$local_path"; then
    # File exists and has markers — replace between markers
    local before after
    before=$(sed '/<!-- HELM BEGIN -->/,$d' "$local_path")
    after=$(sed '1,/<!-- HELM END -->/d' "$local_path")
    {
      printf '%s\n' "$before"
      printf '<!-- HELM BEGIN -->\n'
      cat "$tmp_file"
      printf '\n<!-- HELM END -->\n'
      printf '%s' "$after"
    } > "$local_path"
    echo "UPDATED $local_path (replaced content between HELM markers)"
  else
    # File exists but no markers — append
    printf '\n<!-- HELM BEGIN -->\n' >> "$local_path"
    cat "$tmp_file" >> "$local_path"
    printf '\n<!-- HELM END -->\n' >> "$local_path"
    echo "APPENDED to $local_path (added HELM markers at end)"
  fi

  rm -f "$tmp_file"
}

merge_helm_file "AGENTS.md" "https://raw.githubusercontent.com/smartmarbles/helm/main/AGENTS.md"
merge_helm_file ".github/copilot-instructions.md" "https://raw.githubusercontent.com/smartmarbles/helm/main/.github/copilot-instructions.md"
merge_helm_file "CLAUDE.md" "https://raw.githubusercontent.com/smartmarbles/helm/main/CLAUDE.md"
```

### PowerShell (Windows)

Run the following function, then call it for both files:

```powershell
function Merge-HelmFile {
  param(
    [string]$LocalPath,
    [string]$RemoteUrl
  )
  $tmpFile = [System.IO.Path]::GetTempFileName()
  Invoke-WebRequest -Uri $RemoteUrl -OutFile $tmpFile -UseBasicParsing

  # Back up existing file before modification
  if (Test-Path $LocalPath) {
    Copy-Item -Path $LocalPath -Destination "$LocalPath.bak" -Force
    Write-Host "BACKUP created: $LocalPath.bak"
  }

  $remoteContent = Get-Content -Path $tmpFile -Raw
  $beginMarker = "<!-- HELM BEGIN -->"
  $endMarker = "<!-- HELM END -->"
  $wrapped = "$beginMarker`n$remoteContent`n$endMarker"

  if (-not (Test-Path $LocalPath)) {
    # File does not exist — create with markers
    Set-Content -Path $LocalPath -Value $wrapped -NoNewline
    Write-Host "CREATED $LocalPath (with HELM markers)"
  }
  elseif ((Get-Content -Path $LocalPath -Raw) -match [regex]::Escape($beginMarker)) {
    # File exists and has markers — replace between markers
    $existing = Get-Content -Path $LocalPath -Raw
    $pattern = "(?s)$([regex]::Escape($beginMarker)).*?$([regex]::Escape($endMarker))"
    $updated = [regex]::Replace($existing, $pattern, $wrapped)
    Set-Content -Path $LocalPath -Value $updated -NoNewline
    Write-Host "UPDATED $LocalPath (replaced content between HELM markers)"
  }
  else {
    # File exists but no markers — append
    Add-Content -Path $LocalPath -Value "`n$wrapped"
    Write-Host "APPENDED to $LocalPath (added HELM markers at end)"
  }

  Remove-Item -Path $tmpFile -Force
}

Merge-HelmFile -LocalPath "AGENTS.md" -RemoteUrl "https://raw.githubusercontent.com/smartmarbles/helm/main/AGENTS.md"
Merge-HelmFile -LocalPath ".github/copilot-instructions.md" -RemoteUrl "https://raw.githubusercontent.com/smartmarbles/helm/main/.github/copilot-instructions.md"
Merge-HelmFile -LocalPath "CLAUDE.md" -RemoteUrl "https://raw.githubusercontent.com/smartmarbles/helm/main/CLAUDE.md"
```

---

## Step 3a: Reconcile team-roster.md

### Rationale

`.github/team-roster.md` is not like the other paths in the File Manifest's "Regular files" bucket. Every other regular file is pure Helm-authored content with no legitimate local edits to protect, so a plain overwrite on every run is correct. `team-roster.md` is different: a consuming project hires and archives agents into it over time, so overwriting it on an update would silently erase real local history. This step reconciles the file instead of downloading over it, using only the current local file and the freshly-downloaded upstream file — each row's `Source` column (`Helm core` or `Local hire`) is what makes that reconciliation possible without a third, local-only bookkeeping file.

### Mechanical setup

Fetch the current upstream copy, and check whether a local copy already exists, before doing any row-level comparison.

#### bash (macOS / Linux)

```bash
BASE_URL="https://raw.githubusercontent.com/smartmarbles/helm/main"
TMP_UPSTREAM=$(mktemp)
curl -fsSL "$BASE_URL/.github/team-roster.md" -o "$TMP_UPSTREAM" || { echo "ERROR: failed to download .github/team-roster.md from upstream."; exit 1; }

LOCAL_EXISTS=false
[ -f ".github/team-roster.md" ] && LOCAL_EXISTS=true

echo "Local team-roster.md exists: $LOCAL_EXISTS"
```

#### PowerShell (Windows)

```powershell
$baseUrl = "https://raw.githubusercontent.com/smartmarbles/helm/main"
$tmpUpstream = [System.IO.Path]::GetTempFileName()
Invoke-WebRequest -Uri "$baseUrl/.github/team-roster.md" -OutFile $tmpUpstream -UseBasicParsing

$localExists = Test-Path ".github/team-roster.md"

Write-Host "Local team-roster.md exists: $localExists"
```

### Case: local `team-roster.md` does not exist (fresh install)

No reconciliation is needed — there is no local state to protect yet.

1. Write the downloaded upstream content directly to `.github/team-roster.md`.
2. Stop. Do not run the comparison logic below for this file on this run.

### Case: local `team-roster.md` exists — reconcile

Perform the comparison below **independently for each of the two known table sections**, `## Permanent Team` and `## Temporary Agents`, matching rows across the local file and the newly-downloaded upstream file by their first column (the Agent name). This comparison is row-level judgment, not mechanical text transformation — carry it out directly as the executing agent rather than trying to force it into a shell one-liner, the same way this repo already expects an agent (not a script) to carry out the Human Checkpoint / open-question protocol described in `AGENTS.md`.

For each table section, classify every Agent name found across new-upstream ∪ current-local into exactly one of the following, then act accordingly:

- **New upstream entries** — present in new-upstream, absent from local (by name) → add this row to the local table, using the new-upstream row's full content (including its `Source: Helm core` value).
- **Candidates for removal** — a local row tagged `Source: Helm core` whose name is absent from the newly-downloaded upstream file → do **not** remove automatically. Collect every such name across both table sections into a single list.
- **Local-only entries** — a local row tagged `Source: Local hire` → always keep, untouched. Never ask about these; they are the user's own hires and are never a candidate for removal here.
- **Untagged legacy rows (migration case)** — a local row that has no `Source` column value at all (from before this feature existed):
  - If its name is present in the newly-downloaded upstream file, treat it as `Helm core` for this run's classification (making it eligible for the removal-candidate check on a *future* run) and backfill `Source: Helm core` into the row on write-back.
  - If its name is absent from upstream, treat it as `Local hire` and backfill `Source: Local hire` into the row on write-back.
  - After this one-time backfill, every row in the local file carries an explicit tag going forward.
- **Unchanged entries** — a name present in both local and new-upstream, and already explicitly tagged → keep the local row's content exactly as-is. Do not overwrite locally-edited fields (Role, Use When, Hired, Tagline) of a row just because the name also exists upstream — this step reconciles row *presence*, not per-field wording.

Once every table section has been classified, if the "candidates for removal" list is non-empty, pause and ask the user a direct question naming every candidate, in this form (adapt the wording naturally, but preserve the meaning):

> "Helm's upstream team roster no longer lists the following agent(s): `<names>`. They're still in your local roster. OK for me to remove them, or would you like to keep them?"

Wait for an explicit answer before proceeding further.
- If the user declines for a given name, leave that row in place, untouched.
- If the user approves for a given name, remove that row from the local table.

If the "candidates for removal" list is empty, skip the question and proceed directly.

### Final write-back (both cases)

Write the reconciled table content back to `.github/team-roster.md`. There is no second file to write — the `Source` column on each row is the only provenance record this mechanism needs.

### Never guess

Never delete a row from `.github/team-roster.md` without the explicit user confirmation described above. If upstream has restructured the table or headings in a way that does not map cleanly onto this procedure (e.g. a table section renamed, the `Source` column removed, rows no longer matching on name), do not improvise a mapping — pause and ask the user how to proceed.

---

## Step 4: Download regular files

Download every file listed under **Regular files** in the File Manifest. Use the base URL from the manifest for the remote path — that remote path is always the manifest's literal `.helm/...` text, regardless of any local rename. For the **local destination path**, any path with a `.helm/` prefix must use the `HELM_ROOT`/`$helmRoot` value resolved in Step 1a in place of the literal `.helm` segment — every other prefix is used as-is from the manifest. This substitution happens only when computing where to actually write the file; it never means editing the manifest text itself. These are simple overwrites — no merge logic.

### bash (macOS / Linux)

Build a `FILES` array from the **Regular files** list in the manifest, then run:

```bash
BASE_URL="https://raw.githubusercontent.com/smartmarbles/helm/main"
for f in "${FILES[@]}"; do
  DEST="$f"
  case "$f" in
    .helm/*) DEST="$HELM_ROOT/${f#.helm/}" ;;
  esac
  curl -fsSL "$BASE_URL/$f" -o "$DEST"
done
echo "Downloaded ${#FILES[@]} files."
```

### PowerShell (Windows)

Build a `$files` array from the **Regular files** list in the manifest, then run:

```powershell
$baseUrl = "https://raw.githubusercontent.com/smartmarbles/helm/main"
foreach ($f in $files) {
  $dest = $f
  if ($f -like ".helm/*") {
    $dest = "$helmRoot/" + $f.Substring(".helm/".Length)
  }
  Invoke-WebRequest -Uri "$baseUrl/$f" -OutFile $dest -UseBasicParsing
}
Write-Host "Downloaded $($files.Count) files."
```

---

## Step 5: Vendor the `skills-ref` package

Unlike every other regular file, `.github/scripts/vendor/skills-ref/` is not fetched with a plain `curl`/`Invoke-WebRequest` — it is a pinned subdirectory of an external monorepo, cloned via `git` at a fixed commit so `validate_skill.py` always runs against a known-good, reviewed version.

- **Upstream repository:** `https://github.com/agentskills/agentskills`
- **Subdirectory:** `skills-ref/`
- **Pinned commit:** `69ef37e9424c0a7ea9dd2293b559e43ec8176379`

If `.github/scripts/vendor/skills-ref/VENDOR_INFO.md` already exists and names this same pinned commit, skip this step — the vendored copy is already current.

### bash (macOS / Linux)

```bash
TMP_DIR=$(mktemp -d)
git clone --no-checkout --filter=blob:none https://github.com/agentskills/agentskills.git "$TMP_DIR" || { echo "ERROR: git clone of agentskills/agentskills failed."; exit 1; }
git -C "$TMP_DIR" sparse-checkout init --cone || { echo "ERROR: git sparse-checkout init failed."; exit 1; }
git -C "$TMP_DIR" sparse-checkout set skills-ref || { echo "ERROR: git sparse-checkout set skills-ref failed."; exit 1; }
git -C "$TMP_DIR" checkout 69ef37e9424c0a7ea9dd2293b559e43ec8176379 || { echo "ERROR: git checkout of pinned commit 69ef37e9424c0a7ea9dd2293b559e43ec8176379 failed."; exit 1; }
rm -rf .github/scripts/vendor/skills-ref || { echo "ERROR: removing existing .github/scripts/vendor/skills-ref failed."; exit 1; }
mkdir -p .github/scripts/vendor || { echo "ERROR: creating .github/scripts/vendor directory failed."; exit 1; }
cp -r "$TMP_DIR/skills-ref" .github/scripts/vendor/skills-ref || { echo "ERROR: copying skills-ref into .github/scripts/vendor failed."; exit 1; }
find .github/scripts/vendor/skills-ref -name "__pycache__" -type d -exec rm -rf {} +
COMMIT_DATE=$(git -C "$TMP_DIR" show -s --format=%cd --date=short 69ef37e9424c0a7ea9dd2293b559e43ec8176379)
VENDORED_ON=$(date +%Y-%m-%d)
cat > .github/scripts/vendor/skills-ref/VENDOR_INFO.md <<EOF
# Vendored: skills-ref

- Source: https://github.com/agentskills/agentskills (monorepo subdirectory skills-ref/)
- Pinned commit: 69ef37e9424c0a7ea9dd2293b559e43ec8176379
- Pinned date: $COMMIT_DATE (commit date)
- Vendored on: $VENDORED_ON
- License: Apache-2.0 (see LICENSE in this directory)
- No PyPI distribution exists for this package; it is vendored per its own README's disclaimer that it is a demonstration library, not production tooling.
- Runtime dependencies (not vendored, installed separately): click>=8.0, strictyaml>=1.7.3.
- Not modified from upstream. Do not hand-edit files under src/skills_ref/; re-vendor from a newer pinned commit instead.
EOF
if [ $? -ne 0 ]; then
  echo "ERROR: writing .github/scripts/vendor/skills-ref/VENDOR_INFO.md failed."
  exit 1
fi
rm -rf "$TMP_DIR"
if [ -f .github/scripts/vendor/skills-ref/VENDOR_INFO.md ] && grep -q "69ef37e9424c0a7ea9dd2293b559e43ec8176379" .github/scripts/vendor/skills-ref/VENDOR_INFO.md; then
  echo "Vendored skills-ref at 69ef37e9424c0a7ea9dd2293b559e43ec8176379."
else
  echo "ERROR: .github/scripts/vendor/skills-ref/VENDOR_INFO.md was not created or does not name the pinned commit — vendoring did not complete successfully."
  exit 1
fi
```

### PowerShell (Windows)

```powershell
$tmpDir = Join-Path $env:TEMP ([System.IO.Path]::GetRandomFileName())
git clone --no-checkout --filter=blob:none https://github.com/agentskills/agentskills.git $tmpDir
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: git clone of agentskills/agentskills failed."; exit 1 }
git -C $tmpDir sparse-checkout init --cone
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: git sparse-checkout init failed."; exit 1 }
git -C $tmpDir sparse-checkout set skills-ref
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: git sparse-checkout set skills-ref failed."; exit 1 }
git -C $tmpDir checkout 69ef37e9424c0a7ea9dd2293b559e43ec8176379
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: git checkout of pinned commit 69ef37e9424c0a7ea9dd2293b559e43ec8176379 failed."; exit 1 }
try {
  if (Test-Path -Path ".github/scripts/vendor/skills-ref") {
    Remove-Item -Recurse -Force ".github/scripts/vendor/skills-ref" -ErrorAction Stop
  }
  New-Item -ItemType Directory -Force -Path ".github/scripts/vendor" -ErrorAction Stop | Out-Null
} catch {
  Write-Host "ERROR: removing existing .github/scripts/vendor/skills-ref or creating .github/scripts/vendor failed: $_"
  exit 1
}
try {
  Copy-Item -Recurse -Path (Join-Path $tmpDir "skills-ref") -Destination ".github/scripts/vendor/skills-ref" -ErrorAction Stop
} catch {
  Write-Host "ERROR: copying skills-ref into .github/scripts/vendor failed: $_"
  exit 1
}
Get-ChildItem -Path ".github/scripts/vendor/skills-ref" -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
$commitDate = (git -C $tmpDir show -s --format=%cd --date=short 69ef37e9424c0a7ea9dd2293b559e43ec8176379)
$vendoredOn = Get-Date -Format "yyyy-MM-dd"
$vendorInfo = @"
# Vendored: skills-ref

- Source: https://github.com/agentskills/agentskills (monorepo subdirectory skills-ref/)
- Pinned commit: 69ef37e9424c0a7ea9dd2293b559e43ec8176379
- Pinned date: $commitDate (commit date)
- Vendored on: $vendoredOn
- License: Apache-2.0 (see LICENSE in this directory)
- No PyPI distribution exists for this package; it is vendored per its own README's disclaimer that it is a demonstration library, not production tooling.
- Runtime dependencies (not vendored, installed separately): click>=8.0, strictyaml>=1.7.3.
- Not modified from upstream. Do not hand-edit files under src/skills_ref/; re-vendor from a newer pinned commit instead.
"@
try {
  Set-Content -Path ".github/scripts/vendor/skills-ref/VENDOR_INFO.md" -Value $vendorInfo -ErrorAction Stop
} catch {
  Write-Host "ERROR: writing .github/scripts/vendor/skills-ref/VENDOR_INFO.md failed: $_"
  exit 1
}
Remove-Item -Recurse -Force $tmpDir
$vendorInfoPath = ".github/scripts/vendor/skills-ref/VENDOR_INFO.md"
$vendorInfoValid = $false
if (Test-Path -Path $vendorInfoPath -PathType Leaf) {
  if (Select-String -Path $vendorInfoPath -Pattern "69ef37e9424c0a7ea9dd2293b559e43ec8176379" -Quiet) {
    $vendorInfoValid = $true
  }
}
if ($vendorInfoValid) {
  Write-Host "Vendored skills-ref at 69ef37e9424c0a7ea9dd2293b559e43ec8176379."
} else {
  Write-Host "ERROR: .github/scripts/vendor/skills-ref/VENDOR_INFO.md was not created or does not name the pinned commit — vendoring did not complete successfully."
  exit 1
}
```

---

## Step 5a: Optional — install `click` and `strictyaml` for manual `validate_skill.py` runs

`.github/scripts/validate_skill.py` is normally invoked through Helm's own tooling, but if a user runs it manually, the vendored `skills-ref` CLI it delegates to requires `click>=8.0` and `strictyaml>=1.7.3` at runtime — these are not vendored and must be installed separately. Use the Python interpreter confirmed in Step 1's prerequisite check.

This check is **non-blocking**: if the `pip install` fails, print a warning and continue with the rest of bootstrap rather than aborting.

### bash (macOS / Linux)

```bash
if ! python3 -c "import click, strictyaml" >/dev/null 2>&1; then
  echo "click/strictyaml not found — installing (non-blocking)..."
  if pip install "click>=8.0" "strictyaml>=1.7.3"; then
    echo "Installed click and strictyaml."
  else
    echo "WARNING: failed to install click/strictyaml. Run 'pip install \"click>=8.0\" \"strictyaml>=1.7.3\"' manually before using validate_skill.py directly. Continuing bootstrap."
  fi
else
  echo "click and strictyaml already present."
fi
```

### PowerShell (Windows)

```powershell
python -c "import click, strictyaml" 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host "click/strictyaml not found — installing (non-blocking)..."
  pip install "click>=8.0" "strictyaml>=1.7.3"
  if ($LASTEXITCODE -eq 0) {
    Write-Host "Installed click and strictyaml."
  } else {
    Write-Host "WARNING: failed to install click/strictyaml. Run 'pip install ""click>=8.0"" ""strictyaml>=1.7.3""' manually before using validate_skill.py directly. Continuing bootstrap."
  }
} else {
  Write-Host "click and strictyaml already present."
}
```

---

## Step 6: Validate installation

Verify that every file and directory from the **File Manifest** exists on disk. This covers all three categories (merge-safe, regular — including `hook.py` — and the vendored `skills-ref` package, checked by confirming `VENDOR_INFO.md` names the pinned commit). Directories are derived from file paths (same as Step 2).

Collect any missing items and report pass/fail.

### bash (macOS / Linux)

Build directory and file lists from the manifest, then check each:

```bash
missing=()

# Validate directories (derived from all manifest file paths)
for d in <space-separated unique parent directories>; do
  [ -d "$d" ] || missing+=("DIR $d")
done

# Validate all files (merge-safe + regular)
for f in <space-separated list of all expected files>; do
  [ -f "$f" ] || missing+=("FILE $f")
done

# Validate the vendored skills-ref package's VENDOR_INFO.md names the pinned commit
VENDOR_INFO=".github/scripts/vendor/skills-ref/VENDOR_INFO.md"
if [ ! -f "$VENDOR_INFO" ] || ! grep -q "69ef37e9424c0a7ea9dd2293b559e43ec8176379" "$VENDOR_INFO"; then
  missing+=("FILE $VENDOR_INFO (missing or does not name pinned commit 69ef37e9424c0a7ea9dd2293b559e43ec8176379)")
fi

if [ ${#missing[@]} -gt 0 ]; then
  echo "Validation FAILED — ${#missing[@]} item(s) missing:"
  for item in "${missing[@]}"; do
    echo "  $item"
  done
else
  echo "All files and directories verified."
fi
```

### PowerShell (Windows)

Build directory and file lists from the manifest, then check each:

```powershell
$missing = @()

# Validate directories (derived from all manifest file paths)
$expectedDirs = @(<list>)
foreach ($d in $expectedDirs) {
  if (-not (Test-Path -Path $d -PathType Container)) {
    $missing += "DIR $d"
  }
}

# Validate all files (merge-safe + regular)
$expectedFiles = @(<list>)
foreach ($f in $expectedFiles) {
  if (-not (Test-Path -Path $f -PathType Leaf)) {
    $missing += "FILE $f"
  }
}

# Validate the vendored skills-ref package's VENDOR_INFO.md names the pinned commit
$vendorInfoPath = ".github/scripts/vendor/skills-ref/VENDOR_INFO.md"
$vendorInfoValid = $false
if (Test-Path -Path $vendorInfoPath -PathType Leaf) {
  if (Select-String -Path $vendorInfoPath -Pattern "69ef37e9424c0a7ea9dd2293b559e43ec8176379" -Quiet) {
    $vendorInfoValid = $true
  }
}
if (-not $vendorInfoValid) {
  $missing += "FILE $vendorInfoPath (missing or does not name pinned commit 69ef37e9424c0a7ea9dd2293b559e43ec8176379)"
}

if ($missing.Count -gt 0) {
  Write-Host "Validation FAILED — $($missing.Count) item(s) missing:"
  foreach ($item in $missing) {
    Write-Host "  $item"
  }
} else {
  Write-Host "All files and directories verified."
}
```

---

## Step 7: Print summary

After all steps complete, print a summary including:

- Total directories created
- Total files downloaded
- The Python interpreter resolved in Step 1's prerequisite check (command and version, e.g. `python3 — Python 3.11.4`)
- The vendored `skills-ref` commit hash confirmed
- The click/strictyaml check outcome from Step 5a (ALREADY PRESENT / INSTALLED / FAILED — non-blocking)
- The merge action taken for `AGENTS.md` (CREATED / UPDATED / APPENDED)
- The merge action taken for `.github/copilot-instructions.md` (CREATED / UPDATED / APPENDED)
- The merge action taken for `CLAUDE.md` (CREATED / UPDATED / APPENDED)
- Validation result from Step 6 (PASSED / FAILED with count of missing items)
- A confirmation line: **"Helm bootstrap complete."**
