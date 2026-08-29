"""Markdown draft parser for SCR records (spec015 Task 11.3).

Parses an agent-authored markdown draft file into a flat dict of record
fields.  The draft format is a YAML-style frontmatter block delimited by
``---`` lines, followed by an optional prose body that is ignored.

Frontmatter syntax accepted:

* ``key: value`` — string value (surrounding whitespace stripped)
* ``key:`` (empty value) — stored as empty string
* Lines starting with ``#`` and blank lines are ignored

No third-party YAML library is used; the parser handles only flat
``key: value`` pairs, which is sufficient for all v1 SCR record classes.

Example draft::

    ---
    record_class: approval
    workflow_id: wf-abc
    session_id: sess-xyz
    turn_id: t-001
    approved_by: ARTHUR
    decision: allow
    tool_name: create_file
    tool_use_id: tu-001
    ---

    Optional prose body follows (ignored by the parser).
"""

from __future__ import annotations

from pathlib import Path


class DraftParseError(Exception):
    """Raised when a draft file cannot be parsed into a record dict."""


def parse(draft_path: Path) -> dict[str, str]:
    """Parse *draft_path* and return a flat ``{key: value}`` dict.

    Raises :class:`DraftParseError` if the file cannot be read or does not
    contain a valid ``---`` frontmatter block.
    """
    try:
        text = draft_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DraftParseError(f"cannot read draft file {draft_path}: {exc}") from exc

    lines = text.splitlines()
    start = _find_delimiter(lines, 0)
    if start is None:
        raise DraftParseError(
            f"draft {draft_path} has no opening '---' frontmatter delimiter"
        )
    end = _find_delimiter(lines, start + 1)
    if end is None:
        raise DraftParseError(
            f"draft {draft_path} has no closing '---' frontmatter delimiter"
        )

    result: dict[str, str] = {}
    for raw_line in lines[start + 1 : end]:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise DraftParseError(
                f"draft {draft_path} has malformed frontmatter line: {raw_line!r}"
            )
        key, _, value = line.partition(":")
        result[key.strip()] = value.strip()

    return result


def _find_delimiter(lines: list[str], start: int) -> int | None:
    for index in range(start, len(lines)):
        if lines[index].strip() == "---":
            return index
    return None
