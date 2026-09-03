---
description: Bootstrap the Helm multi-agent orchestration system into the current workspace by downloading all required files from GitHub.
---

# Bootstrap Helm Multi-Agent System

You are bootstrapping the **Helm** multi-agent orchestration system into the current VS Code workspace. You must execute all steps below **in order** using terminal commands. Do NOT use file-creation tools — all files must be created via terminal commands (`curl`, `Invoke-WebRequest`, `mkdir`, etc.).

---

## File Manifest

This is the **single source of truth** for all files managed by this bootstrap. Every subsequent step references this manifest — no file paths are defined elsewhere. When adding or removing files from Helm, update ONLY this manifest.

**Base URL:** `https://raw.githubusercontent.com/smartmarbles/helm/main/`

### Merge-safe files
These files may already exist with user content. They are wrapped in `<!-- HELM BEGIN -->` / `<!-- HELM END -->` markers (see Step 3).

| Local path | Remote path |
|---|---|
| `AGENTS.md` | `AGENTS.md` |
| `.github/copilot-instructions.md` | `.github/copilot-instructions.md` |

### Regular files
These files are downloaded directly (overwrite if they exist).

```
.github/team-roster.md
.github/agents/arthur.agent.md
.github/agents/forge.agent.md
.github/agents/merlin.agent.md
.github/agents/quill.agent.md
.github/agents/quiz.agent.md
.github/agents/sage.agent.md
.github/agents/scoop.agent.md
.github/agents/temps/.gitkeep
.github/docs/memory-fallback.md
.github/docs/session-protocol.md
.github/hooks/hooks.json
.github/hooks/scripts/hook.py
.github/playbooks/archive-agent/archive-agent.md
.github/playbooks/conduct-research/conduct-research.md
.github/playbooks/create-plan/create-plan.md
.github/playbooks/create-spec/create-spec.md
.github/playbooks/hire-agent/hire-agent.md
.github/playbooks/quizler/quizler.md
.github/playbooks/skill-creator/skill-creator.md
.github/playbooks/write-technical-docs/write-technical-docs.md
.github/scripts/copilot_token_analyzer.py
.github/scripts/token_proxy.py
.github/scripts/validate_skill.py
.github/skills/skill.instructions.md
.github/skills/orchestrate-delegation/SKILL.md
.github/skills/orchestrate-delegation/evals/evals.json
.github/skills/orchestrate-delegation/references/worked-examples.md
.github/templates/adr-template.md
.github/templates/definition-entry-template.md
.github/templates/plan-template.md
.github/templates/quiz-handoff-template.md
.github/templates/spec-template.md
artifacts/.gitkeep
artifacts/docs/.gitkeep
```

The hook script (`hook.py`) is a single cross-platform Python 3 file used unchanged on Windows, macOS, and Linux — `hooks.json` selects the right launcher (`python` vs `python3`) per OS, not a different script.

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

## Step 6: Validate installation

Verify that every file and directory from the **File Manifest** exists on disk. This covers both categories (merge-safe and regular, including `hook.py`). Directories are derived from file paths (same as Step 2).

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
- The merge action taken for `AGENTS.md` (CREATED / UPDATED / APPENDED)
- The merge action taken for `.github/copilot-instructions.md` (CREATED / UPDATED / APPENDED)
- Validation result from Step 6 (PASSED / FAILED with count of missing items)
- A confirmation line: **"Helm bootstrap complete."**
