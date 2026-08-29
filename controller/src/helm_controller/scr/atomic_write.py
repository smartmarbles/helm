"""Atomic SCR file writer (spec015 Task 11.2).

Implements steps 1-4 of the queue-processor protocol:

1. Validate the record dict against its JSON Schema.
2. Write serialized JSON to a ``.tmp`` sibling of the destination path.
3. Re-validate the ``.tmp`` file content against the schema.
4. Rename via ``os.replace()`` — atomic on Linux and Windows.
   MUST NOT use ``os.rename()``, which raises ``FileExistsError`` on Windows
   when the target already exists.

On any failure between steps 2 and 4 the ``.tmp`` file is deleted before
re-raising so no partial temporary file is ever left on disk.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from helm_controller.contracts._jsonschema_lite import SchemaValidator

_LOGGER = logging.getLogger(__name__)


class AtomicWriteError(Exception):
    """Raised when a validated atomic write cannot be completed."""


def write_record(
    dest_path: Path,
    record: dict[str, Any],
    validator: SchemaValidator,
) -> None:
    """Write *record* to *dest_path* atomically, validating before and after.

    Raises :class:`AtomicWriteError` on validation failure or I/O error.
    The ``.tmp`` file is guaranteed absent when this function returns (whether
    via success or failure).
    """
    errors = validator.collect(record)
    if errors:
        raise AtomicWriteError(
            f"pre-write validation failed for {dest_path.name}: "
            + "; ".join(msg for _, msg in errors)
        )

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest_path.parent / (dest_path.name + ".tmp")
    data = json.dumps(record, ensure_ascii=False, indent=2).encode("utf-8")
    try:
        tmp_path.write_bytes(data)
    except OSError as exc:
        raise AtomicWriteError(f"failed to write tmp file {tmp_path}: {exc}") from exc

    try:
        try:
            reloaded: dict[str, Any] = json.loads(tmp_path.read_bytes())
        except (OSError, json.JSONDecodeError) as exc:
            raise AtomicWriteError(
                f"failed to read back tmp file {tmp_path}: {exc}"
            ) from exc

        post_errors = validator.collect(reloaded)
        if post_errors:
            raise AtomicWriteError(
                f"post-write validation failed for {tmp_path.name}: "
                + "; ".join(msg for _, msg in post_errors)
            )

        os.replace(tmp_path, dest_path)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            _LOGGER.warning("could not remove tmp file %s after failure", tmp_path)
        raise
