#!/usr/bin/env python3
"""Validate an agentskills.io skill directory for compliance.

Checks:
    1. SKILL.md exists
    2. Frontmatter has required fields (name, description)
    3. Frontmatter has no forbidden fields
    4. name matches parent directory name
    5. description length is 10-1024 chars and contains "use" trigger language
    6. scripts/ has at least one .py file
    7. Every .py script has an `if __name__` block
    8. evals/evals.json exists with at least 1 test case
    9. No vendor-specific terms in SKILL.md or scripts
    10. SKILL.md body is under 500 lines

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

# --- agentskills.io spec-allowed frontmatter fields ---
ALLOWED_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}

# --- Vendor-specific terms to flag ---
VENDOR_TERMS_RE = re.compile(
    r"\bclaude\b|\banthropic\b|\bclaude[\s-]?code\b|\bclaude\.ai\b|\banthropic[\s-]?sdk\b",
    re.IGNORECASE,
)

# --- Directories to skip (not project skills) ---
SKIP_DIRS = {"skill-creator"}

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
        return None, content, "SKILL.md does not start with YAML frontmatter (---)"

    end = content.find("---", 3)
    if end == -1:
        return None, content, "SKILL.md has opening --- but no closing ---"

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

    # 1. SKILL.md exists
    skill_md_path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md_path):
        errors.append("SKILL.md not found")
        return {"skill": skill_name, "valid": False, "errors": errors, "warnings": warnings}

    content = _read_file(skill_md_path)
    if not content.strip():
        errors.append("SKILL.md is empty")
        return {"skill": skill_name, "valid": False, "errors": errors, "warnings": warnings}

    # 2. Parse frontmatter
    fm, body, fm_err = _parse_frontmatter(content)
    if fm_err:
        errors.append(fm_err)
        return {"skill": skill_name, "valid": False, "errors": errors, "warnings": warnings}

    # 3. Required fields
    if "name" not in fm:
        errors.append("Frontmatter missing required field: name")
    if "description" not in fm:
        errors.append("Frontmatter missing required field: description")

    # 4. Forbidden fields
    forbidden = set(fm.keys()) - ALLOWED_FIELDS
    # Allow nested keys under metadata (our parser flattens, so just check top-level)
    if forbidden:
        errors.append(f"Frontmatter has forbidden fields: {', '.join(sorted(forbidden))}")

    # 5. Name matches directory
    if "name" in fm and fm["name"] != skill_name:
        errors.append(f"name field '{fm['name']}' does not match directory name '{skill_name}'")

    # 6. Name format (lowercase kebab-case, no consecutive hyphens)
    if "name" in fm:
        name_val = fm["name"]
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name_val):
            errors.append(f"name '{name_val}' is not valid kebab-case (lowercase alphanumeric + single hyphens)")
        if len(name_val) > 64:
            errors.append(f"name is {len(name_val)} chars (max 64)")

    # 7. Description quality
    if "description" in fm:
        desc = fm["description"]
        if len(desc) < MIN_DESC_LEN:
            errors.append(f"description is only {len(desc)} chars (min {MIN_DESC_LEN})")
        if len(desc) > MAX_DESC_LEN:
            errors.append(f"description is {len(desc)} chars (max {MAX_DESC_LEN})")
        # Check for trigger language
        trigger_words = ["use this", "use when", "always use", "use for", "whenever"]
        has_trigger = any(tw in desc.lower() for tw in trigger_words)
        if not has_trigger:
            warnings.append("description lacks trigger language ('Use this skill when...') — may reduce discoverability")

    # 8. Scripts directory
    scripts_dir = os.path.join(skill_dir, "scripts")
    py_scripts = []
    if os.path.isdir(scripts_dir):
        py_scripts = [
            f for f in os.listdir(scripts_dir)
            if f.endswith(".py") and not f.startswith("__")
        ]
    if not py_scripts:
        errors.append("No Python scripts found in scripts/")

    # 9. __main__ blocks in scripts
    for script_name in py_scripts:
        script_path = os.path.join(scripts_dir, script_name)
        script_content = _read_file(script_path)
        if 'if __name__' not in script_content:
            errors.append(f"scripts/{script_name} missing `if __name__ == '__main__':` block")

    # 10. evals/evals.json
    evals_path = os.path.join(skill_dir, "evals", "evals.json")
    if not os.path.isfile(evals_path):
        warnings.append("evals/evals.json not found — skill has no test cases")
    else:
        try:
            evals_data = json.loads(_read_file(evals_path))
            evals_list = evals_data.get("evals", [])
            if len(evals_list) < 1:
                warnings.append("evals/evals.json has no test cases")
            elif len(evals_list) < 3:
                warnings.append(f"evals/evals.json has only {len(evals_list)} test cases (recommend 3+)")
        except (json.JSONDecodeError, AttributeError):
            errors.append("evals/evals.json is not valid JSON")

    # 11. Vendor-specific terms in SKILL.md body
    for i, line in enumerate(content.split("\n"), 1):
        if VENDOR_TERMS_RE.search(line):
            errors.append(f"SKILL.md line {i}: vendor-specific term detected")
            break  # One error is enough to flag it

    # 12. Vendor-specific terms in scripts
    for script_name in py_scripts:
        script_path = os.path.join(scripts_dir, script_name)
        script_content = _read_file(script_path)
        for i, line in enumerate(script_content.split("\n"), 1):
            if VENDOR_TERMS_RE.search(line):
                errors.append(f"scripts/{script_name} line {i}: vendor-specific term detected")
                break

    # 13. SKILL.md body length
    body_lines = len(body.split("\n")) if body else 0
    if body_lines > MAX_BODY_LINES:
        warnings.append(f"SKILL.md body is {body_lines} lines (recommended max {MAX_BODY_LINES})")

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
            status = "✅ PASS" if r["valid"] else "❌ FAIL"
            print(f"\n{status}  {r['skill']}")
            for e in r["errors"]:
                print(f"  ERROR: {e}")
                total_errors += 1
            for w in r["warnings"]:
                print(f"  WARN:  {w}")
                total_warnings += 1

        print(f"\n{'-' * 50}")
        print(f"Skills: {len(results)}  |  Errors: {total_errors}  |  Warnings: {total_warnings}")
        failed = [r for r in results if not r["valid"]]
        if failed:
            print(f"FAILED: {', '.join(r['skill'] for r in failed)}")

    sys.exit(0 if all(r["valid"] for r in results) else 1)


if __name__ == "__main__":
    main()
