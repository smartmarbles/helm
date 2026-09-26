#!/usr/bin/env python3
"""Detect drift between Helm's host-neutral authored sources and per-host agent wrappers.

Background: each Helm agent has exactly one authored source (`.helm/agents/<name>.md`,
the file a human edits) and one thin wrapper per host discovery path
(`.github/agents/<name>.agent.md`, `.claude/agents/<name>.md`, `.devin/agents/<name>.md`,
`.cursor/agents/<name>.md`). The capability-vocabulary-to-host-identifier mapping lives in
exactly one place: the binding reference table in the repo's SOR-A document
(`sor-a-multi-host-binding.md`). This script parses that table directly at runtime rather
than carrying its own copy of the same identifiers, since a second hardcoded list would
itself be the kind of drift-prone duplication this script exists to prevent.

Checks:
    (a) Binding-reference leakage: every concrete host tool identifier in the SOR-A binding
        reference table must not appear (as an inline-code span) anywhere else in the repo,
        except inside a wrapper's own frontmatter block or inside the SOR-A file itself.
    (b) Generated-wrapper-body drift: a wrapper whose body does not match the standard
        instruction-pointer template is treated as having taken the generated-body fallback;
        its body must match its authored source's body exactly.
    (c) name/description duplication drift: each wrapper's frontmatter `name`/`description`
        must match its authored source's `name`/`description`.
    (d) Stale identity references: if the authored-source directory was ever renamed, no
        reference to its prior name may remain. Configurable via --old-helm-name /
        --current-helm-name so this is testable without an actual historical rename.

Usage:
    # Scan the repo this script lives in
    python .github/scripts/check_wrapper_drift.py

    # Scan an explicit path
    python .github/scripts/check_wrapper_drift.py /path/to/repo

    # JSON output
    python .github/scripts/check_wrapper_drift.py --json

    # Test check (d) against a hypothetical prior directory name
    python .github/scripts/check_wrapper_drift.py --old-helm-name .agents-legacy
"""

import argparse
import json
import os
import re
import sys
from typing import Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # .github/scripts -> .github -> repo root

DEFAULT_HELM_DIR_NAME = ".helm"
SOR_A_FILENAME = "sor-a-multi-host-binding.md"
SCAN_TEXT_EXTENSIONS = {".md", ".mdx", ".txt"}
SKIP_DIR_NAMES = {".git", "node_modules", "__pycache__", ".venv", "venv", ".pytest_cache", ".agent-memory"}
IGNORED_TABLE_MARKERS = {"unverified", "unavailable"}
CELL_SOURCE_SPLIT_RE = re.compile(r"\s[—–]\s")  # "identifier — source" convention (em/en dash)

# host key -> (wrapper home dir relative to repo root, filename suffix)
WRAPPER_HOME = {
    "vscode": {"dir": ".github/agents", "suffix": ".agent.md"},
    "claude": {"dir": ".claude/agents", "suffix": ".md"},
    "devin": {"dir": ".devin/agents", "suffix": ".md"},
    "cursor": {"dir": ".cursor/agents", "suffix": ".md"},
}

FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)
BACKTICK_RE = re.compile(r"`([^`\n]+)`")


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def split_frontmatter(content: str):
    """Return (frontmatter_text, body, body_line_offset). frontmatter_text is '' if none."""
    m = FRONTMATTER_RE.match(content)
    if not m:
        return "", content, 0
    return m.group(1), content[m.end():], content[: m.end()].count("\n")


def parse_frontmatter_field(frontmatter_text: str, field: str):
    m = re.search(rf"^{re.escape(field)}:\s*(.+?)\s*$", frontmatter_text, re.MULTILINE)
    if not m:
        return None
    value = m.group(1).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def normalize_block(text: str) -> str:
    lines = [line.rstrip() for line in text.strip("\n").splitlines()]
    return "\n".join(lines).strip()


def iter_text_files(root: str, skip_dirs: set[str] = SKIP_DIR_NAMES, extensions: set[str] = SCAN_TEXT_EXTENSIONS):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for name in filenames:
            if os.path.splitext(name)[1].lower() in extensions:
                yield os.path.join(dirpath, name)


def find_sor_a_path(root: str, override: str | None = None):
    if override:
        return override if os.path.isabs(override) else os.path.join(root, override)
    for path in iter_text_files(root):
        if os.path.basename(path) == SOR_A_FILENAME:
            return path
    return None


def extract_table_identifiers(sor_a_text: str) -> set[str]:
    """Parse the '| Verb | ... |' binding reference table; return the set of host identifiers.

    The Verb column (first cell of each row) is skipped — those are capability-vocabulary
    names, not host tool identifiers. Within each host cell, only backtick tokens appearing
    *before* the cell's " — source/reasoning" dash (the table's own stated convention: "every
    binding cell holds either a published identifier ... or unverified ... or unavailable")
    count as bound identifiers; a cell's prose after the dash routinely cross-references other
    verbs or field names in backticks (e.g. "(see `find-files` ambiguity note)"), which are not
    themselves bindings and must not be captured. The literal markers `unverified`/`unavailable`
    are skipped too; they denote absence of evidence, not an identifier to search for.
    """
    identifiers: set[str] = set()
    in_table = False
    for line in sor_a_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("| Verb |"):
            in_table = True
            continue
        if not in_table:
            continue
        if not stripped.startswith("|"):
            in_table = False
            continue
        core = stripped.replace("|", "").replace("-", "").replace(" ", "")
        if core == "":
            continue  # header separator row
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        for cell in cells[1:]:  # skip the Verb column
            dash_match = CELL_SOURCE_SPLIT_RE.search(cell)
            binding_part = cell[: dash_match.start()] if dash_match else cell
            for match in BACKTICK_RE.finditer(binding_part):
                token = match.group(1).strip()
                if token and token.lower() not in IGNORED_TABLE_MARKERS:
                    identifiers.add(token)
    return identifiers


def is_wrapper_file(path: str, root: str):
    """Return the host key if path is a per-host agent wrapper file directly under its
    discovery dir (not a subdirectory, e.g. `.github/agents/temps/`), else None."""
    rel = os.path.relpath(path, root).replace(os.sep, "/")
    for host, spec in WRAPPER_HOME.items():
        prefix = spec["dir"] + "/"
        if rel.startswith(prefix) and rel.endswith(spec["suffix"]):
            remainder = rel[len(prefix):]
            if "/" not in remainder:
                return host
    return None


def iter_wrapper_files(root: str):
    """Yield (host, path, agent_name) for every wrapper file found directly under a
    host's discovery dir."""
    for host, spec in WRAPPER_HOME.items():
        wrapper_dir = os.path.join(root, spec["dir"])
        if not os.path.isdir(wrapper_dir):
            continue
        for entry in sorted(os.listdir(wrapper_dir)):
            path = os.path.join(wrapper_dir, entry)
            if os.path.isfile(path) and entry.endswith(spec["suffix"]):
                agent_name = entry[: -len(spec["suffix"])].lower()
                yield host, path, agent_name


def canonical_pointer_body(agent_name: str, helm_dir_name: str) -> str:
    """The Mandatory-Read Template body (AGENTS.md), substituting only the source path."""
    source_path = f"{helm_dir_name}/agents/{agent_name}.md"
    return (
        f"> **MANDATORY READ — `{source_path}`**\n"
        ">\n"
        f"> Before performing this task, you MUST read `{source_path}` in full. This is not "
        "optional. Do not improvise from memory. If the file cannot be loaded, STOP and report "
        "the failure — do not proceed without it. Failure to load is a protocol violation.\n"
    )


def check_binding_reference_leakage(root: str, identifiers: set[str], sor_a_path: str, scan_artifacts: bool) -> list[dict[str, Any]]:
    """(a) Fail on any table identifier found outside wrapper frontmatter or SOR-A itself.

    Approximation: only inline-code-span occurrences (`` `Token` ``) are matched, not bare
    words. Several table identifiers (`Read`, `Write`, `Edit`, `Agent`, ...) are common
    English words; without this restriction, ordinary prose ("read the file", capitalized
    sentence-initial "Write") would flood the report with false positives. The table itself,
    and this check's own brief, reference identifiers the same way (backtick-quoted), so this
    is the natural boundary for "quoted as a literal identifier" versus "used as a word".

    `artifacts/` is excluded by default: those are process/research documents (specs, plans,
    research write-ups) that legitimately cite and discuss real host tool identifiers as
    design input, distinct from the shared instruction content (`.helm/`, `AGENTS.md`,
    playbooks, skills) FR-017's leakage rule targets. Pass --scan-artifacts for a stricter,
    repo-wide sweep including artifacts/.

    Residual limitation: a few table identifiers are also ordinary English/vocabulary words
    (`read`, `edit`, `agent`, `search`, `todo`, ...). A backtick-quoted generic usage in shared
    prose (e.g. "use the `read` tools") is indistinguishable, from raw text alone, from a
    genuine leaked identifier. Such hits are reported rather than silently suppressed; treat a
    single-common-word hit as needing a human read of the surrounding sentence.
    """
    findings: list[dict[str, Any]] = []
    skip_dirs = set(SKIP_DIR_NAMES)
    if not scan_artifacts:
        skip_dirs.add("artifacts")
    sor_a_norm = os.path.normpath(sor_a_path)
    for path in iter_text_files(root, skip_dirs=skip_dirs):
        if os.path.normpath(path) == sor_a_norm:
            continue
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        content = _read(path)
        if is_wrapper_file(path, root):
            _, search_text, line_offset = split_frontmatter(content)
        else:
            search_text, line_offset = content, 0
        for idx, line in enumerate(search_text.splitlines(), start=1):
            for match in BACKTICK_RE.finditer(line):
                token = match.group(1).strip()
                if token in identifiers:
                    findings.append({
                        "file": rel,
                        "line": idx + line_offset,
                        "identifier": token,
                        "issue": f"identifier `{token}` found outside wrapper frontmatter and the binding reference file",
                    })
    return findings


def check_generated_body_drift(root: str, helm_dir_name: str):
    """(b) Fail if a generated (non-pointer) wrapper body diverges from its authored source.

    Approximation: there is no stored provenance (hash, timestamp) recording "this body was
    generated from commit X of the authored source", so "generated then diverged" cannot be
    distinguished from "hand-written and never matched". A wrapper body is treated as having
    taken the FR-010 generated-body fallback whenever it does not match the standard
    instruction-pointer template; its content is then compared directly against its authored
    source's current body. This produces the same practical result the check exists for
    (fail when out of sync) without requiring historical provenance.
    """
    findings: list[dict[str, Any]] = []
    generated_count = 0
    helm_agents_dir = os.path.join(root, helm_dir_name, "agents")
    for _host, path, agent_name in iter_wrapper_files(root):
        rel_wrapper = os.path.relpath(path, root).replace(os.sep, "/")
        _, body, _ = split_frontmatter(_read(path))
        if normalize_block(body) == normalize_block(canonical_pointer_body(agent_name, helm_dir_name)):
            continue  # instruction-pointer mode; nothing for this check to compare
        generated_count += 1
        source_path = os.path.join(helm_agents_dir, f"{agent_name}.md")
        if not os.path.isfile(source_path):
            findings.append({
                "file": rel_wrapper,
                "issue": f"generated-body wrapper does not match the instruction-pointer template, and no authored source exists at {helm_dir_name}/agents/{agent_name}.md to check it against",
            })
            continue
        _, source_body, _ = split_frontmatter(_read(source_path))
        if normalize_block(body) != normalize_block(source_body):
            findings.append({
                "file": rel_wrapper,
                "issue": f"generated body has diverged from its authored source at {helm_dir_name}/agents/{agent_name}.md",
            })
    return findings, generated_count


def check_name_description_drift(root: str, helm_dir_name: str):
    """(c) Fail if a wrapper's frontmatter name/description diverges from its authored source."""
    findings: list[dict[str, Any]] = []
    helm_agents_dir = os.path.join(root, helm_dir_name, "agents")
    for _host, path, agent_name in iter_wrapper_files(root):
        rel_wrapper = os.path.relpath(path, root).replace(os.sep, "/")
        source_path = os.path.join(helm_agents_dir, f"{agent_name}.md")
        if not os.path.isfile(source_path):
            findings.append({
                "file": rel_wrapper,
                "issue": f"no authored source found at {helm_dir_name}/agents/{agent_name}.md to check name/description against",
            })
            continue
        w_fm, _, _ = split_frontmatter(_read(path))
        s_fm, _, _ = split_frontmatter(_read(source_path))
        rel_source = os.path.relpath(source_path, root).replace(os.sep, "/")
        w_name, s_name = parse_frontmatter_field(w_fm, "name"), parse_frontmatter_field(s_fm, "name")
        w_desc, s_desc = parse_frontmatter_field(w_fm, "description"), parse_frontmatter_field(s_fm, "description")
        if w_name != s_name:
            findings.append({
                "file": rel_wrapper,
                "issue": f"frontmatter name {w_name!r} does not match authored source {rel_source} name {s_name!r}",
            })
        if w_desc != s_desc:
            findings.append({
                "file": rel_wrapper,
                "issue": f"frontmatter description does not match authored source {rel_source}",
            })
    return findings


def check_stale_identity_references(root: str, old_helm_name: str | None) -> tuple[list[dict[str, Any]], bool]:
    """(d) Fail if any reference to a prior/renamed authored-source directory name remains.

    No maintained history of prior `.helm/`-equivalent names exists (it has never been
    renamed in this repo), so this is implemented as a configurable old-name-vs-current-name
    check via --old-helm-name rather than something that requires an actual historical
    rename to test. When no old name is configured, this check is skipped (not failed).
    """
    findings: list[dict[str, Any]] = []
    if not old_helm_name:
        return findings, False
    for path in iter_text_files(root):
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        content = _read(path)
        for idx, line in enumerate(content.splitlines(), start=1):
            if old_helm_name in line:
                findings.append({
                    "file": rel,
                    "line": idx,
                    "issue": f"references stale identity name '{old_helm_name}'",
                })
    return findings, True


def run_checks(root: str, sor_a_override: str | None, old_helm_name: str | None, current_helm_name: str, scan_artifacts: bool) -> dict[str, Any]:
    sor_a_path = find_sor_a_path(root, sor_a_override)
    if not sor_a_path:
        return {"fatal": f"SOR-A binding reference file not found (expected a file named '{SOR_A_FILENAME}' under {root})"}

    identifiers = extract_table_identifiers(_read(sor_a_path))
    if not identifiers:
        rel_sor_a = os.path.relpath(sor_a_path, root).replace(os.sep, "/")
        return {"fatal": f"no capability-vocabulary identifiers parsed from the binding reference table in {rel_sor_a}"}

    leakage = check_binding_reference_leakage(root, identifiers, sor_a_path, scan_artifacts)
    body_findings, generated_count = check_generated_body_drift(root, current_helm_name)
    nd_findings = check_name_description_drift(root, current_helm_name)
    stale_findings, stale_configured = check_stale_identity_references(root, old_helm_name)

    checks: dict[str, dict[str, Any]] = {
        "a_binding_reference_leakage": {
            "description": "Concrete host tool identifiers from the binding reference table, found outside wrapper frontmatter and the binding reference file.",
            "findings": leakage,
            "passed": len(leakage) == 0,
        },
        "b_generated_wrapper_body_drift": {
            "description": "Per-host wrapper bodies not using the instruction-pointer mechanism, checked for divergence from their authored source.",
            "findings": body_findings,
            "generated_body_wrappers_detected": generated_count,
            "passed": len(body_findings) == 0,
        },
        "c_name_description_drift": {
            "description": "Wrapper frontmatter name/description checked against their authored source.",
            "findings": nd_findings,
            "passed": len(nd_findings) == 0,
        },
        "d_stale_identity_references": {
            "description": "References to a prior/renamed authored-source directory name.",
            "configured": stale_configured,
            "findings": stale_findings,
            "passed": len(stale_findings) == 0,
        },
    }
    return {
        "sor_a_path": os.path.relpath(sor_a_path, root).replace(os.sep, "/"),
        "identifiers_checked": sorted(identifiers),
        "checks": checks,
        "passed": all(c["passed"] for c in checks.values()),
    }


def print_human_summary(report: dict[str, Any]):
    labels = [
        ("a_binding_reference_leakage", "(a) Binding-reference leakage"),
        ("b_generated_wrapper_body_drift", "(b) Generated-wrapper-body drift"),
        ("c_name_description_drift", "(c) name/description duplication drift"),
        ("d_stale_identity_references", "(d) Stale identity references"),
    ]
    print(f"SOR-A binding reference: {report['sor_a_path']}", file=sys.stderr)
    print(f"Identifiers checked: {len(report['identifiers_checked'])}", file=sys.stderr)

    total_findings = 0
    for key, label in labels:
        check = report["checks"][key]
        status = "[PASS]" if check["passed"] else "[FAIL]"
        print(f"\n{status}  {label}", file=sys.stderr)
        if key == "d_stale_identity_references" and not check.get("configured", True):
            print("  SKIPPED: no --old-helm-name configured (nothing to check)", file=sys.stderr)
            continue
        if key == "b_generated_wrapper_body_drift":
            print(f"  generated-body wrappers detected: {check['generated_body_wrappers_detected']}", file=sys.stderr)
        for finding in check["findings"]:
            total_findings += 1
            line_part = f":{finding['line']}" if "line" in finding else ""
            print(f"  {finding['file']}{line_part}  {finding['issue']}", file=sys.stderr)

    print(f"\n{'-' * 50}", file=sys.stderr)
    print(f"Total findings: {total_findings}", file=sys.stderr)
    print("RESULT: CLEAN" if report["passed"] else "RESULT: DRIFT FOUND", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Detect drift between Helm's host-neutral authored sources (.helm/) and per-host agent wrappers."
    )
    parser.add_argument("path", nargs="?", default=REPO_ROOT, help="Repo root to scan (default: this script's own repo)")
    parser.add_argument("--sor-a-path", dest="sor_a_path", default=None, help="Explicit path to the SOR-A binding reference file (default: search the repo for its filename)")
    parser.add_argument("--current-helm-name", dest="current_helm_name", default=DEFAULT_HELM_DIR_NAME, help="Current name of the host-neutral authored-source directory (default: .helm)")
    parser.add_argument("--old-helm-name", dest="old_helm_name", default=None, help="Prior/renamed name of the authored-source directory to flag as stale (default: none; check (d) is skipped)")
    parser.add_argument("--scan-artifacts", action="store_true", help="Include artifacts/ in the binding-reference leakage sweep (default: excluded; see check (a) docstring)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output as JSON")
    args = parser.parse_args()

    root = os.path.abspath(args.path)
    report = run_checks(root, args.sor_a_path, args.old_helm_name, args.current_helm_name, args.scan_artifacts)

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
