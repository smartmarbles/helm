"""SCR importer: external commit path for agent-authored markdown drafts (spec015 Task 11.3).

The importer is the ONLY permitted external path to commit SCR records.
Internal controller-initiated commits (e.g., approval records written at
gate-pass time) bypass the markdown-draft step but MUST still go through the
write queue and schema validation.

Flow:

1. Parse the draft file via :func:`~helm_controller.scr.draft_parser.parse`.
2. Verify that ``record_class`` is present and a known v1 class.
3. Auto-fill ``record_id``, ``created_at``, and ``scr_schema_version`` when
   absent from the draft (these are importer-managed fields).
4. Enqueue the assembled record through the write queue, which validates
   against the JSON Schema and commits atomically.

Returns :class:`~helm_controller.scr.write_queue.WriteResult` to the caller.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from helm_controller.scr.draft_parser import DraftParseError, parse
from helm_controller.scr.identity import new_record_id
from helm_controller.scr.write_queue import (
    KNOWN_RECORD_CLASSES,
    SCR_SCHEMA_VERSION,
    ScrWriteQueue,
    WriteResult,
)

_LOGGER = logging.getLogger(__name__)


class ImportError(Exception):
    """Raised when an import cannot proceed before reaching the write queue."""


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def import_draft(draft_path: Path, queue: ScrWriteQueue) -> WriteResult:
    """Parse *draft_path*, assemble a record, and commit via *queue*.

    Returns a :class:`WriteResult` with ``success=False`` and an error
    message when the draft is invalid or the write fails.
    """
    try:
        fields = parse(draft_path)
    except DraftParseError as exc:
        _LOGGER.error("SCR importer: parse failure: %s", exc)
        return WriteResult(success=False, error=str(exc))

    record_class = fields.get("record_class")
    if not record_class:
        msg = f"draft {draft_path} missing required 'record_class' field"
        _LOGGER.error("SCR importer: %s", msg)
        return WriteResult(success=False, error=msg)

    if record_class not in KNOWN_RECORD_CLASSES:
        msg = (
            f"draft {draft_path} has unknown record_class {record_class!r}; "
            f"known classes: {sorted(KNOWN_RECORD_CLASSES)}"
        )
        _LOGGER.error("SCR importer: %s", msg)
        return WriteResult(success=False, error=msg)

    record: dict[str, Any] = dict(fields)
    if "record_id" not in record:
        record["record_id"] = new_record_id()
    if "created_at" not in record:
        record["created_at"] = _utcnow_iso()
    if "scr_schema_version" not in record:
        record["scr_schema_version"] = SCR_SCHEMA_VERSION

    return queue.submit(record)
