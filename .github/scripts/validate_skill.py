#!/usr/bin/env python3
"""Validate an agentskills.io skill directory for compliance.

Checks:
    1. SKILL.md exists
    2. Frontmatter has required fields (name, description)
    3. Frontmatter has no forbidden fields
    4. name matches parent directory name
    5. description length is 10-1024 chars and contains "use" trigger language
    6. scripts/ has at least one .py file (only when scripts/ is present)
    7. Every .py script has an `if __name__` block (only when scripts/ is present)
    8. evals/evals.json exists (error if missing)
    9. SKILL.md body is under 500 lines (warning)
    10. "NOT for:" clause present in description or body (warning if absent)
    11. SKILL.md body does not reference skill-relative files that do not exist (warning)

Usage:
    # Validate a single skill
    python .github/scripts/validate_skill.py .github/skills/token-counting

    # Validate all skills in a directory
    python .github/scripts/validate_skill.py .github/skills/ --all

    # JSON output
    python .github/scripts/validate_skill.py .github/skills/token-counting --json
"""

import argparse
import json
import os
import re
import sys

# --- agentskills.io + VS Code Copilot-native spec-allowed frontmatter fields ---
ALLOWED_FIELDS = {
    "name", "description", "license", "compatibility", "metadata",
    "allowed-tools", "argument-hint", "user-invocable", "disable-model-invocation",
}

# --- Directories to skip (not project skills) ---
SKIP_DIRS = {"skill-creator"}

# --- Library files exempt from CLI entry-point rules (E-MISSING-MAIN, W-MISSING-SHEBANG) ---
LIBRARY_FILE_NAMES = {"__init__.py", "utils.py", "helpers.py"}

# --- Minimum description length for quality ---
MIN_DESC_LEN = 30
MAX_DESC_LEN = 1024
MAX_BODY_LINES = 500


def _read_file(path: str) -> str:
    """Read a file, returning empty string on failure."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except (OSError, IOError):
        return ""


def _parse_frontmatter(content: str):
    """Parse YAML frontmatter from markdown content.

    Returns (frontmatter_dict, body_text, error_msg).
    """
    if not content.startswith("---"):
        return None, content, "E-FRONTMATTER: SKILL.md does not start with YAML frontmatter (---)"

    end = content.find("---", 3)
    if end == -1:
        return None, content, "E-FRONTMATTER: SKILL.md has opening --- but no closing ---"

    fm_text = content[3:end].strip()
    body = content[end + 3:].strip()

    # Simple YAML parsing - handles flat key: value and multi-line description
    fm = {}
    current_key = None
    current_value_lines = []

    for line in fm_text.split("\n"):
        # Check for a new key
        match = re.match(r"^([a-zA-Z_-]+)\s*:\s*(.*)", line)
        if match and not line.startswith("  ") and not line.startswith("\t"):
            # Save previous key
            if current_key is not None:
                fm[current_key] = "\n".join(current_value_lines).strip()
            current_key = match.group(1)
            current_value_lines = [match.group(2).strip()]
        elif current_key is not None:
            # Continuation line (multi-line value like description: >)
            current_value_lines.append(line.strip())

    # Save last key
    if current_key is not None:
        fm[current_key] = "\n".join(current_value_lines).strip()

    # Clean up ">" or "|" block scalar indicators
    for k, v in fm.items():
        if v.startswith(">") or v.startswith("|"):
            fm[k] = v[1:].strip()

    return fm, body, None


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

    # 2. Parse frontmatter
    fm, body, fm_err = _parse_frontmatter(content)
    if fm_err:
        errors.append(fm_err)
        return {"skill": skill_name, "valid": False, "errors": errors, "warnings": warnings}

    # 3. Required fields
    if "name" not in fm:
        errors.append("E-REQUIRED-FIELD: Frontmatter missing required field: name")
    if "description" not in fm:
        errors.append("E-REQUIRED-FIELD: Frontmatter missing required field: description")

    # 4. Forbidden fields
    forbidden = set(fm.keys()) - ALLOWED_FIELDS
    # Allow nested keys under metadata (our parser flattens, so just check top-level)
    for field in sorted(forbidden):
        if field == "version":
            errors.append(f"E-FORBIDDEN-FIELD: forbidden field '{field}' (move under metadata:)")
        elif field in ("model", "tools"):
            errors.append(f"E-FORBIDDEN-FIELD: forbidden field '{field}' (agent-frontmatter field, not a skill field)")
        else:
            errors.append(f"E-FORBIDDEN-FIELD: forbidden field '{field}'")

    # 5. Name matches directory
    if "name" in fm and fm["name"] != skill_name:
        errors.append(f"E-NAME-MISMATCH: name field '{fm['name']}' does not match directory name '{skill_name}'")

    # 6. Name format (lowercase kebab-case, no consecutive hyphens)
    if "name" in fm:
        name_val = fm["name"]
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name_val):
            errors.append(f"E-NAME-FORMAT: name '{name_val}' is not valid kebab-case (lowercase alphanumeric + single hyphens)")
        if len(name_val) > 64:
            errors.append(f"E-NAME-FORMAT: name is {len(name_val)} chars (max 64)")

    # 7. Description quality
    if "description" in fm:
        desc = fm["description"]
        if len(desc) < MIN_DESC_LEN:
            errors.append(f"E-DESCRIPTION: description is only {len(desc)} chars (min {MIN_DESC_LEN})")
        if len(desc) > MAX_DESC_LEN:
            errors.append(f"E-DESCRIPTION: description is {len(desc)} chars (max {MAX_DESC_LEN})")
        # Check for trigger language
        trigger_words = ["use this", "use when", "always use", "use for", "whenever"]
        has_trigger = any(tw in desc.lower() for tw in trigger_words)
        if not has_trigger:
            warnings.append("W-TRIGGER-LANGUAGE: description lacks trigger language ('Use this skill when...') — may reduce discoverability")

    # 8. Scripts directory (conditional — only validate if scripts/ exists)
    scripts_dir = os.path.join(skill_dir, "scripts")
    py_scripts = []
    if os.path.isdir(scripts_dir):
        py_scripts = [
            f for f in os.listdir(scripts_dir)
            if f.endswith(".py") and not f.startswith("__")
        ]
        if not py_scripts:
            errors.append("FR-093: scripts/ directory exists but contains no .py files")

    # 9. __main__ blocks + shebang in CLI scripts (library files exempt — Change A)
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

    # 10. evals/evals.json (FR-093: absence is now an error) — skipped for third-party
    if not is_third_party:
        evals_path = os.path.join(skill_dir, "evals", "evals.json")
        if not os.path.isfile(evals_path):
            errors.append("FR-093: evals/evals.json not found — skill has no test cases")
        else:
            try:
                evals_data = json.loads(_read_file(evals_path))
                evals_list = evals_data.get("evals", [])
                if len(evals_list) < 1:
                    errors.append("FR-093: evals/evals.json has no test cases")
                elif len(evals_list) < 3:
                    warnings.append(f"FR-034: evals/evals.json has only {len(evals_list)} test cases (recommend 3+)")
            except (json.JSONDecodeError, AttributeError):
                errors.append("E-EVALS-JSON: evals/evals.json is not valid JSON")

    # 11. SKILL.md body length
    body_lines = len(body.split("\n")) if body else 0
    if body_lines > MAX_BODY_LINES:
        warnings.append(f"W-BODY-LENGTH: SKILL.md body is {body_lines} lines (recommended max {MAX_BODY_LINES})")

    # 12. "NOT for:" clause presence (FR-094) — skipped for third-party
    if not is_third_party:
        desc_text = fm.get("description", "") if fm else ""
        has_not_for = "not for:" in desc_text.lower() or "not for:" in body.lower()
        if not has_not_for:
            warnings.append("W-MISSING-NOT-FOR: SKILL.md has no \"NOT for:\" clause in description or body")

    # 13. Progressive-disclosure heuristic (FR-094): warn on unresolved skill-relative file refs — skipped for third-party
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
            seen_refs.add(bare_m.group(1))
        for ref in sorted(seen_refs):
            if not os.path.exists(os.path.join(skill_dir, ref)):
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
