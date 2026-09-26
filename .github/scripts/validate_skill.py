#!/usr/bin/env python3
"""Validate an agentskills.io skill directory for compliance.

Frontmatter parsing and structural conformance (required fields, forbidden
fields, name format, name/directory match, description length ceiling) are
delegated to the vendored `skills-ref` conformance oracle
(`.github/scripts/vendor/skills-ref/`) rather than hand-rolled here.

Checks:
    1. SKILL.md exists and is non-empty
    2. Frontmatter/name/description conformance (via skills-ref `validate`)
    3. Description has a minimum length and contains "use" trigger language
    4. scripts/ has at least one .py file (only when scripts/ is present)
    5. Every .py script has an `if __name__` block (only when scripts/ is present)
    6. evals/evals.json exists (error if missing)
    7. SKILL.md body is under 500 lines (warning)
    8. "NOT for:" clause present in description or body (warning if absent)
    9. SKILL.md body does not reference skill-relative files that do not exist (warning)

Requires the vendored skills-ref CLI's runtime dependencies to be installed:
    pip install "click>=8.0" "strictyaml>=1.7.3"

Usage:
    # Validate a single skill
    python .github/scripts/validate_skill.py .claude/skills/token-counting

    # Validate all skills in a directory
    python .github/scripts/validate_skill.py .claude/skills/ --all

    # JSON output
    python .github/scripts/validate_skill.py .claude/skills/token-counting --json
"""

import argparse
import json
import os
import re
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_REF_SRC = os.path.join(SCRIPT_DIR, "vendor", "skills-ref", "src")

# --- Directories to skip (not project skills) ---
SKIP_DIRS = set()

# --- Library files exempt from CLI entry-point rules (E-MISSING-MAIN, W-MISSING-SHEBANG) ---
LIBRARY_FILE_NAMES = {"__init__.py", "utils.py", "helpers.py"}

# --- Minimum description length for quality (skills-ref only enforces a maximum) ---
MIN_DESC_LEN = 30
MAX_BODY_LINES = 500


def _read_file(path: str) -> str:
    """Read a file, returning empty string on failure."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except (OSError, IOError):
        return ""


def _extract_body(content: str) -> str:
    """Return the markdown body following the YAML frontmatter block.

    This only locates the closing `---` delimiter; it does not parse YAML
    keys (that parsing is delegated to skills-ref).
    """
    if not content.startswith("---"):
        return content
    end = content.find("---", 3)
    if end == -1:
        return content
    return content[end + 3:].strip()


def _skills_ref_env() -> dict:
    """Build a subprocess environment with the vendored skills-ref package importable."""
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join([SKILLS_REF_SRC, existing]) if existing else SKILLS_REF_SRC
    return env


def _run_skills_ref(args: list) -> subprocess.CompletedProcess:
    """Run the vendored skills-ref CLI as a subprocess with an argument list (no shell)."""
    cmd = [sys.executable, "-m", "skills_ref.cli"] + args
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=_skills_ref_env(),
            check=False,
        )
    except OSError as exc:
        raise RuntimeError(f"failed to launch vendored skills-ref CLI: {exc}") from exc


def _check_skills_ref_available() -> None:
    """Fail fast with a clear message if skills-ref's runtime dependencies are missing."""
    try:
        result = _run_skills_ref(["--help"])
    except RuntimeError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        sys.exit(2)

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or "unknown error"
        print(
            f"FATAL: vendored skills-ref CLI failed to run ({detail}).\n"
            'Install its runtime dependencies: pip install "click>=8.0" "strictyaml>=1.7.3"',
            file=sys.stderr,
        )
        sys.exit(2)


def _skills_ref_validate(skill_dir: str) -> list:
    """Run skills-ref's `validate` command and return Helm-formatted error strings."""
    result = _run_skills_ref(["validate", skill_dir])
    if result.returncode == 0:
        return []

    errors = []
    for line in result.stderr.splitlines():
        line = line.strip()
        if line.startswith("- "):
            errors.append(f"E-SKILLS-REF: {line[2:].strip()}")
    if not errors:
        detail = result.stderr.strip() or result.stdout.strip() or "validation failed with no detail"
        errors.append(f"E-SKILLS-REF: {detail}")
    return errors


def _skills_ref_read_properties(skill_dir: str):
    """Run skills-ref's `read-properties` command and return the parsed dict, or None on failure."""
    result = _run_skills_ref(["read-properties", skill_dir])
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def validate_skill(skill_dir: str) -> dict:
    """Validate a single skill directory.

    Returns a dict with:
        skill: directory name
        valid: bool
        errors: list of error strings
        warnings: list of warning strings
    """
    skill_name = os.path.basename(os.path.normpath(skill_dir))
    errors = []
    warnings = []

    # 0a. SKIP_DIRS short-circuit (B2): clean pass with informational note
    if skill_name in SKIP_DIRS:
        warnings.append(f"W-SKIPPED: {skill_name} is in SKIP_DIRS; validation skipped")
        return {"skill": skill_name, "valid": True, "errors": errors, "warnings": warnings}

    # 0b. Third-party skill detection (B1): LICENSE file at root signals carve-out
    is_third_party = (
        os.path.exists(os.path.join(skill_dir, "LICENSE"))
        or os.path.exists(os.path.join(skill_dir, "LICENSE.txt"))
    )
    if is_third_party:
        warnings.append("W-THIRD-PARTY: LICENSE file detected; skipping authoring-rule checks (evals, NOT-for clause, progressive-disclosure)")

    # 1. SKILL.md exists
    skill_md_path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md_path):
        errors.append("E-SKILL-MD: SKILL.md not found")
        return {"skill": skill_name, "valid": False, "errors": errors, "warnings": warnings}

    content = _read_file(skill_md_path)
    if not content.strip():
        errors.append("E-SKILL-MD: SKILL.md is empty")
        return {"skill": skill_name, "valid": False, "errors": errors, "warnings": warnings}

    body = _extract_body(content)

    # 2. Frontmatter/name/description structural conformance — delegated to skills-ref.
    errors.extend(_skills_ref_validate(skill_dir))
    props = _skills_ref_read_properties(skill_dir)
    desc = props.get("description", "") if props else ""

    # 3. Description quality (min length + trigger language) — Helm house rules;
    #    skills-ref only enforces a maximum length, not these.
    if props is not None:
        if len(desc) < MIN_DESC_LEN:
            errors.append(f"E-DESCRIPTION: description is only {len(desc)} chars (min {MIN_DESC_LEN})")
        trigger_words = ["use this", "use when", "always use", "use for", "whenever"]
        has_trigger = any(tw in desc.lower() for tw in trigger_words)
        if not has_trigger:
            warnings.append("W-TRIGGER-LANGUAGE: description lacks trigger language ('Use this skill when...') — may reduce discoverability")

    # 4. Scripts directory (conditional — only validate if scripts/ exists)
    scripts_dir = os.path.join(skill_dir, "scripts")
    py_scripts = []
    if os.path.isdir(scripts_dir):
        py_scripts = [
            f for f in os.listdir(scripts_dir)
            if f.endswith(".py") and not f.startswith("__")
        ]
        if not py_scripts:
            errors.append("E-EMPTY-SCRIPTS-DIR: scripts/ directory exists but contains no .py files")

    # 5. __main__ blocks + shebang in CLI scripts (library files exempt — Change A)
    for script_name in py_scripts:
        script_path = os.path.join(scripts_dir, script_name)
        script_content = _read_file(script_path)
        if script_name in LIBRARY_FILE_NAMES or script_name.startswith("_"):
            continue
        if 'if __name__' not in script_content:
            errors.append(f"E-MISSING-MAIN: scripts/{script_name} missing `if __name__ == '__main__':` block")
            continue
        # Change C: CLI entry points must have shebang as first line
        first_line = script_content.split("\n", 1)[0] if script_content else ""
        if first_line != "#!/usr/bin/env python3":
            warnings.append(f"W-MISSING-SHEBANG: scripts/{script_name} missing `#!/usr/bin/env python3` shebang line")

    # 6. evals/evals.json (absence is an error) — skipped for third-party
    if not is_third_party:
        evals_path = os.path.join(skill_dir, "evals", "evals.json")
        if not os.path.isfile(evals_path):
            errors.append("E-MISSING-EVALS: evals/evals.json not found — skill has no test cases")
        else:
            try:
                evals_data = json.loads(_read_file(evals_path))
                evals_list = evals_data.get("evals", [])
                if len(evals_list) < 1:
                    errors.append("E-EMPTY-EVALS: evals/evals.json has no test cases")
                elif len(evals_list) < 3:
                    warnings.append(f"W-FEW-EVALS: evals/evals.json has only {len(evals_list)} test cases (recommend 3+)")
            except (json.JSONDecodeError, AttributeError):
                errors.append("E-EVALS-JSON: evals/evals.json is not valid JSON")

    # 7. SKILL.md body length
    body_lines = len(body.split("\n")) if body else 0
    if body_lines > MAX_BODY_LINES:
        warnings.append(f"W-BODY-LENGTH: SKILL.md body is {body_lines} lines (recommended max {MAX_BODY_LINES})")

    # 8. "NOT for:" clause presence, checked against skills-ref's parsed description
    #    (not a line-start regex) plus the raw body — skipped for third-party
    if not is_third_party:
        has_not_for = "not for:" in desc.lower() or "not for:" in body.lower()
        if not has_not_for:
            warnings.append("W-MISSING-NOT-FOR: SKILL.md has no \"NOT for:\" clause in description or body")

    # 9. Progressive-disclosure heuristic: warn on unresolved skill-relative file refs — skipped for third-party
    if not is_third_party:
        # Strip fenced code blocks to reduce false positives; leave inline code spans intact
        stripped_body = re.sub(r"```[^\n]*\n.*?```", "", body, flags=re.DOTALL)
        link_re = re.compile(r"\[(?:[^\]]*)]\(([^)]+)\)")
        bare_re = re.compile(r"\b((?:scripts|references|evals|assets)/[a-zA-Z0-9_/.-]+[a-zA-Z0-9])\b")
        seen_refs = set()
        for link_m in link_re.finditer(stripped_body):
            ref = link_m.group(1).strip()
            if "://" not in ref and not ref.startswith("#") and not ref.startswith("/"):
                seen_refs.add(ref)
        for bare_m in bare_re.finditer(stripped_body):
            ref = bare_m.group(1)
            # Skip project-level paths (e.g., .github/scripts/...) — not skill-relative
            start = bare_m.start()
            if start >= 8 and stripped_body[start - 8:start] == '.github/':
                continue
            seen_refs.add(ref)
        for ref in sorted(seen_refs):
            file_ref = ref.split("#")[0]  # strip fragment before path check
            if not os.path.exists(os.path.join(skill_dir, file_ref)):
                warnings.append(f"W-MISSING-FILE: body references '{ref}' but it does not exist in the skill directory")

    return {
        "skill": skill_name,
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def find_skills(base_dir: str) -> list:
    """Find all skill directories under base_dir (directories containing SKILL.md)."""
    skills = []
    if not os.path.isdir(base_dir):
        return skills
    for entry in sorted(os.listdir(base_dir)):
        entry_path = os.path.join(base_dir, entry)
        if os.path.isdir(entry_path) and entry not in SKIP_DIRS:
            if os.path.isfile(os.path.join(entry_path, "SKILL.md")):
                skills.append(entry_path)
    return skills

def main():
    parser = argparse.ArgumentParser(description="Validate agentskills.io skill directories")
    parser.add_argument("path", help="Skill directory or parent directory (with --all)")
    parser.add_argument("--all", action="store_true", help="Validate all skills in the directory")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output as JSON")
    args = parser.parse_args()

    _check_skills_ref_available()

    if args.all:
        skill_dirs = find_skills(args.path)
        if not skill_dirs:
            print(f"No skills found in {args.path}", file=sys.stderr)
            sys.exit(1)
    else:
        skill_dirs = [args.path]

    results = [validate_skill(d) for d in skill_dirs]

    if args.json_output:
        print(json.dumps(results, indent=2))
    else:
        total_errors = 0
        total_warnings = 0
        for r in results:
            status = "[PASS]" if r["valid"] else "[FAIL]"
            print(f"\n{status}  {r['skill']}", file=sys.stderr)
            for e in r["errors"]:
                print(f"  ERROR: {e}", file=sys.stderr)
                total_errors += 1
            for w in r["warnings"]:
                print(f"  WARN:  {w}", file=sys.stderr)
                total_warnings += 1

        print(f"\n{'-' * 50}", file=sys.stderr)
        print(f"Skills: {len(results)}  |  Errors: {total_errors}  |  Warnings: {total_warnings}", file=sys.stderr)
        failed = [r for r in results if not r["valid"]]
        if failed:
            print(f"FAILED: {', '.join(r['skill'] for r in failed)}", file=sys.stderr)

    sys.exit(0 if all(r["valid"] for r in results) else 1)


if __name__ == "__main__":
    main()
