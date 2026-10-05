#!/usr/bin/env python3
"""Detect drift between Helm's bootstrap manifest and the manifest-governed directories.

Background: `.helm/prompts/bootstrap-helm.md`'s "File Manifest" section is the
hand-maintained, documented single source of truth for every file the bootstrap
installer downloads into a consumer workspace. Because it is hand-maintained, it can
silently fall out of sync with the actual tracked files living under the directories
it is supposed to govern (e.g. a new playbook reference file added to disk without a
matching manifest entry). This script parses every file path listed in that section
and diffs it against `git ls-files` scoped to the manifest-governed directories,
rather than carrying a second hardcoded file list of its own — a second list would
itself be the kind of drift-prone duplication this script exists to prevent.

Checks:
    (primary)   Unlisted: every tracked, non-excluded file under a governed root must
                appear in the manifest's parsed listed-paths set. A tracked file that
                isn't listed is a finding — this is the bug class the manifest was
                originally found to have (10 missing playbook files).
    (secondary) Stale listing: every manifest-listed path should correspond to an
                actually-tracked file (per `git ls-files`, not merely "exists on
                disk"). A listed-but-not-tracked path is a finding — the inverse bug
                (the manifest references a file that no longer exists or was never
                committed).

Usage:
    # Scan the repo this script lives in
    python .github/scripts/check_manifest_drift.py

    # Scan an explicit path
    python .github/scripts/check_manifest_drift.py /path/to/repo

    # Point at a different (e.g. scratch/pre-fix) manifest file
    python .github/scripts/check_manifest_drift.py --manifest-path /path/to/manifest.md

    # JSON output
    python .github/scripts/check_manifest_drift.py --json
"""

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # .github/scripts -> .github -> repo root

DEFAULT_MANIFEST_RELPATH = ".helm/prompts/bootstrap-helm.md"
MANIFEST_SECTION_HEADING = "## File Manifest"

# Manifest-governed roots: directories whose tracked files must all be listed in the
# bootstrap manifest. `.helm/` recursively covers `.helm/prompts/` with no separate
# entry needed. `.devin/agents` and `.cursor/agents` are included alongside
# `.claude/agents` and `.github/agents` for parity — same per-host wrapper-dir risk
# class as the original gap.
DEFAULT_GOVERNED_ROOTS = [
    ".helm/",
    ".claude/",
    ".github/agents",
    ".devin/agents",
    ".cursor/agents",
    ".github/docs",
    ".github/templates",
    ".github/scripts",
    ".github/hooks",
]

# This script's own path, relative to repo root. It lives inside the governed
# `.github/scripts/` directory but is maintainer-only tooling, never shipped to
# consumer projects via the bootstrap manifest (confirmed design decision: self-
# exclude rather than add to the manifest).
SELF_PATH = ".github/scripts/check_manifest_drift.py"

# `.helm/prompts/bootstrap-helm.md` and `.helm/prompts/audit-default-agent.prompt.md`
# are maintainer-only authored-source files under the governed `.helm/` root. They
# are intentionally never listed in the bootstrap manifest. (`.github/prompts/` no
# longer exists in this repo at all, so these two `.helm/prompts/` entries are now
# the only prompt-related exclusions needed.) Grouped with SELF_PATH as the same
# class of "lives under a governed root but is never shipped to consumers" exclusion.
MAINTAINER_ONLY_EXCLUSIONS = {
    SELF_PATH,
    ".helm/prompts/bootstrap-helm.md",
    ".helm/prompts/audit-default-agent.prompt.md",
}

VENDOR_PREFIX = ".github/scripts/vendor/skills-ref/"
GITKEEP_NAME = ".gitkeep"

FENCE_RE = re.compile(r"^```")
TABLE_ROW_RE = re.compile(r"^\|(.+)\|\s*$")


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def find_manifest_path(root: str, override: str | None = None) -> str:
    if override:
        return override if os.path.isabs(override) else os.path.join(root, override)
    return os.path.join(root, DEFAULT_MANIFEST_RELPATH)


def extract_manifest_section(manifest_text: str) -> str:
    """Return only the text between '## File Manifest' and the next '## ' heading.

    Steps 1-7 later in the same document repeat several of the manifest's own paths
    inside example shell/PowerShell snippets; bounding extraction to this section is
    what keeps those from being mistaken for additional "listed" entries.
    """
    lines = manifest_text.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if line.strip() == MANIFEST_SECTION_HEADING:
            start = idx + 1
            break
    if start is None:
        return ""
    end = len(lines)
    for idx in range(start, len(lines)):
        if lines[idx].startswith("## "):
            end = idx
            break
    return "\n".join(lines[start:end])


def extract_table_paths(section_text: str) -> set[str]:
    """Extract backtick-quoted first-column paths from the 'Merge-safe files' table.

    This is a markdown table cell, not a fenced code-block line, so it needs separate
    extraction logic from `extract_fenced_block_paths`.
    """
    paths: set[str] = set()
    for line in section_text.splitlines():
        match = TABLE_ROW_RE.match(line.strip())
        if not match:
            continue
        cells = [c.strip() for c in match.group(1).split("|")]
        if not cells:
            continue
        first_cell = cells[0]
        if first_cell.lower() in ("local path", ""):
            continue
        if set(first_cell) == {"-"}:
            continue  # header separator row, e.g. "---"
        cell_match = re.match(r"^`([^`]+)`$", first_cell)
        if cell_match:
            paths.add(cell_match.group(1).strip())
    return paths


def extract_fenced_block_paths(section_text: str) -> set[str]:
    """Extract bare path lines from every fenced code block within the section.

    There are multiple separate fenced blocks in the File Manifest section (agents/
    playbooks, the 28-wrapper block, the skills block, the "remaining supporting
    files" block, and the vendored-package block) — all must be collected, not just
    the first one found.
    """
    paths: set[str] = set()
    in_fence = False
    for line in section_text.splitlines():
        if FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            continue
        if not in_fence:
            continue
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(VENDOR_PREFIX):
            # Directory-tree marker pinned via git, not a single file; carries
            # trailing prose on the same line, e.g. "(pinned upstream commit, ...)".
            continue
        # A bare path line has no trailing prose; take the first whitespace-delimited
        # token to be defensive, but manifest path lines are expected to be pure.
        paths.add(stripped.split()[0])
    return paths


def parse_manifest_listed_paths(manifest_text: str) -> set[str]:
    section_text = extract_manifest_section(manifest_text)
    return extract_table_paths(section_text) | extract_fenced_block_paths(section_text)


def run_git_ls_files(root: str, roots: list[str]) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--"] + roots,
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("git executable not found on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"git ls-files failed: {exc.stderr.strip()}") from exc
    # git ls-files always returns forward-slash paths regardless of OS.
    return [line for line in result.stdout.splitlines() if line.strip()]


def is_excluded(rel_path: str) -> bool:
    if os.path.basename(rel_path) == GITKEEP_NAME:
        return True
    if rel_path.startswith(VENDOR_PREFIX):
        return True
    if rel_path in MAINTAINER_ONLY_EXCLUSIONS:
        return True
    return False


def run_checks(root: str, manifest_override: str | None, governed_roots: list[str]) -> dict[str, Any]:
    manifest_path = find_manifest_path(root, manifest_override)
    if not os.path.isfile(manifest_path):
        return {"fatal": f"bootstrap manifest not found at {manifest_path}"}

    manifest_text = _read(manifest_path)
    section_text = extract_manifest_section(manifest_text)
    if not section_text.strip():
        rel_manifest = os.path.relpath(manifest_path, root).replace(os.sep, "/")
        return {"fatal": f"'{MANIFEST_SECTION_HEADING}' section not found in {rel_manifest}"}

    listed_paths = parse_manifest_listed_paths(manifest_text)
    if not listed_paths:
        return {"fatal": "no file paths parsed from the File Manifest section"}

    try:
        governed_tracked_files = run_git_ls_files(root, governed_roots)
        all_tracked_files = run_git_ls_files(root, [])
    except RuntimeError as exc:
        return {"fatal": str(exc)}

    # git ls-files already returns forward-slash paths relative to cwd (root) on every
    # OS; normalize defensively the same way check_wrapper_drift.py does for
    # filesystem-walked paths, in case a separator ever slips through.
    governed_tracked_rel = {f.replace(os.sep, "/").replace("\\", "/") for f in governed_tracked_files}
    all_tracked_rel = {f.replace(os.sep, "/").replace("\\", "/") for f in all_tracked_files}

    governed_non_excluded = {f for f in governed_tracked_rel if not is_excluded(f)}

    unlisted = sorted(governed_non_excluded - listed_paths)
    unlisted_findings = [
        {"file": f, "issue": "tracked file under a governed root is not listed in the File Manifest"}
        for f in unlisted
    ]

    # Secondary check is repo-wide (not governed-root-scoped): the manifest
    # legitimately lists several files outside the governed roots (AGENTS.md,
    # CLAUDE.md, .github/copilot-instructions.md, .github/team-roster.md,
    # artifacts/.gitkeep, ...), so "is this listed path actually tracked?" must be
    # checked against all tracked files, not just the governed-root subset.
    stale = sorted(listed_paths - all_tracked_rel)
    stale_findings = [
        {"file": f, "issue": "manifest-listed path does not correspond to a tracked file (git ls-files)"}
        for f in stale
    ]

    checks: dict[str, dict[str, Any]] = {
        "primary_unlisted": {
            "description": "Tracked, non-excluded files under governed roots that are not listed in the File Manifest.",
            "findings": unlisted_findings,
            "passed": len(unlisted_findings) == 0,
        },
        "secondary_stale_listing": {
            "description": "Manifest-listed paths that do not correspond to an actually-tracked file.",
            "findings": stale_findings,
            "passed": len(stale_findings) == 0,
        },
    }
    return {
        "manifest_path": os.path.relpath(manifest_path, root).replace(os.sep, "/"),
        "governed_roots": governed_roots,
        "listed_paths_count": len(listed_paths),
        "tracked_governed_files_count": len(governed_non_excluded),
        "checks": checks,
        "passed": all(c["passed"] for c in checks.values()),
    }


def print_human_summary(report: dict[str, Any]) -> None:
    labels = [
        ("primary_unlisted", "Primary: unlisted tracked files"),
        ("secondary_stale_listing", "Secondary: stale manifest listings"),
    ]
    print(f"Bootstrap manifest: {report['manifest_path']}", file=sys.stderr)
    print(f"Listed paths: {report['listed_paths_count']}", file=sys.stderr)
    print(f"Tracked governed files (non-excluded): {report['tracked_governed_files_count']}", file=sys.stderr)

    total_findings = 0
    for key, label in labels:
        check = report["checks"][key]
        status = "[PASS]" if check["passed"] else "[FAIL]"
        print(f"\n{status}  {label}", file=sys.stderr)
        for finding in check["findings"]:
            total_findings += 1
            print(f"  {finding['file']}  {finding['issue']}", file=sys.stderr)

    print(f"\n{'-' * 50}", file=sys.stderr)
    print(f"Total findings: {total_findings}", file=sys.stderr)
    print("RESULT: CLEAN" if report["passed"] else "RESULT: DRIFT FOUND", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect drift between Helm's bootstrap manifest (File Manifest section) and the tracked files in its governed directories."
    )
    parser.add_argument("path", nargs="?", default=REPO_ROOT, help="Repo root to scan (default: this script's own repo)")
    parser.add_argument(
        "--manifest-path",
        dest="manifest_path",
        default=None,
        help=f"Explicit path to the bootstrap manifest (default: {DEFAULT_MANIFEST_RELPATH} under the repo root)",
    )
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output as JSON")
    args = parser.parse_args()

    root = os.path.abspath(args.path)
    report = run_checks(root, args.manifest_path, list(DEFAULT_GOVERNED_ROOTS))

    if "fatal" in report:
        if args.json_output:
            print(json.dumps(report, indent=2))
        else:
            print(f"FATAL: {report['fatal']}", file=sys.stderr)
        sys.exit(2)

    if args.json_output:
        print(json.dumps(report, indent=2))
    else:
        print_human_summary(report)

    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
