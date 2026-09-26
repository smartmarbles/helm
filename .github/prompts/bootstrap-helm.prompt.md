---
description: Bootstrap the Helm multi-agent orchestration system into the current workspace by downloading all required files from GitHub, for use across VS Code Copilot, Claude Code, Devin Desktop, and Cursor.
---

# Bootstrap Helm Multi-Agent System

You are bootstrapping the **Helm** multi-agent orchestration system into the current workspace. This bootstrap prompt itself runs inside a VS Code Copilot chat session (that is simply where `.prompt.md` files are discovered), but the files it installs are what let the resulting project be worked on from **any** of Helm's four supported hosts — VS Code Copilot, Claude Code, Devin Desktop, and Cursor — not VS Code alone. You must execute all steps below **in order** using terminal commands. Do NOT use file-creation tools — all files must be created via terminal commands (`curl`, `Invoke-WebRequest`, `mkdir`, etc.).

---

## File Manifest

This is the **single source of truth** for all files managed by this bootstrap. Every subsequent step references this manifest — no file paths are defined elsewhere. When adding or removing files from Helm, update ONLY this manifest.

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
.helm/playbooks/create-plan/create-plan.md
.helm/playbooks/create-spec/create-spec.md
.helm/playbooks/hire-agent/hire-agent.md
.helm/playbooks/quizler/quizler.md
.helm/playbooks/skill-creator/skill-creator.md
.helm/playbooks/write-technical-docs/write-technical-docs.md
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
.github/team-roster.md
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

### Vendored package

One additional dependency is not a plain file download — it is pinned to a specific upstream commit and vendored via `git`, not `curl`. See Step 5.

```
.github/scripts/vendor/skills-ref/  (pinned upstream commit, see Step 5)
```

---

## Renaming `.helm/`

`.helm/` is Helm's default name for the host-neutral directory holding the authored source of every agent, playbook, and probe. No host reads `.helm/` directly — every host discovers Helm's team only through the per-host wrapper files listed above, each of which points back at a file under `.helm/`.

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

---

## Step 2: Create directories

Extract the parent directory of every file in the manifest (both categories) and create each unique directory. If a directory already exists, skip it silently.

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

## Step 4: Download regular files

Download every file listed under **Regular files** in the File Manifest. Use the base URL from the manifest. These are simple overwrites — no merge logic.

### bash (macOS / Linux)

Build a `FILES` array from the **Regular files** list in the manifest, then run:

```bash
BASE_URL="https://raw.githubusercontent.com/smartmarbles/helm/main"
for f in "${FILES[@]}"; do
  curl -fsSL "$BASE_URL/$f" -o "$f"
done
echo "Downloaded ${#FILES[@]} files."
```

### PowerShell (Windows)

Build a `$files` array from the **Regular files** list in the manifest, then run:

```powershell
$baseUrl = "https://raw.githubusercontent.com/smartmarbles/helm/main"
foreach ($f in $files) {
  Invoke-WebRequest -Uri "$baseUrl/$f" -OutFile $f -UseBasicParsing
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
git clone --no-checkout --filter=blob:none https://github.com/agentskills/agentskills.git "$TMP_DIR"
git -C "$TMP_DIR" sparse-checkout init --cone
git -C "$TMP_DIR" sparse-checkout set skills-ref
git -C "$TMP_DIR" checkout 69ef37e9424c0a7ea9dd2293b559e43ec8176379
rm -rf .github/scripts/vendor/skills-ref
mkdir -p .github/scripts/vendor
cp -r "$TMP_DIR/skills-ref" .github/scripts/vendor/skills-ref
find .github/scripts/vendor/skills-ref -name "__pycache__" -type d -exec rm -rf {} +
rm -rf "$TMP_DIR"
echo "Vendored skills-ref at 69ef37e9424c0a7ea9dd2293b559e43ec8176379."
```

### PowerShell (Windows)

```powershell
$tmpDir = Join-Path $env:TEMP ([System.IO.Path]::GetRandomFileName())
git clone --no-checkout --filter=blob:none https://github.com/agentskills/agentskills.git $tmpDir
git -C $tmpDir sparse-checkout init --cone
git -C $tmpDir sparse-checkout set skills-ref
git -C $tmpDir checkout 69ef37e9424c0a7ea9dd2293b559e43ec8176379
Remove-Item -Recurse -Force ".github/scripts/vendor/skills-ref" -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path ".github/scripts/vendor" | Out-Null
Copy-Item -Recurse -Path (Join-Path $tmpDir "skills-ref") -Destination ".github/scripts/vendor/skills-ref"
Get-ChildItem -Path ".github/scripts/vendor/skills-ref" -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Remove-Item -Recurse -Force $tmpDir
Write-Host "Vendored skills-ref at 69ef37e9424c0a7ea9dd2293b559e43ec8176379."
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
- The vendored `skills-ref` commit hash confirmed
- The merge action taken for `AGENTS.md` (CREATED / UPDATED / APPENDED)
- The merge action taken for `.github/copilot-instructions.md` (CREATED / UPDATED / APPENDED)
- The merge action taken for `CLAUDE.md` (CREATED / UPDATED / APPENDED)
- Validation result from Step 6 (PASSED / FAILED with count of missing items)
- A confirmation line: **"Helm bootstrap complete."**
