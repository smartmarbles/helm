"""SCR write-queue: single-writer serialization for .scr/ file commits (spec015 Task 11.2).

All SCR writes MUST go through this queue.  The queue uses ``queue.Queue``
(stdlib, naturally thread-safe with blocking put/get) — NOT an asyncio queue.
The HTTP server is ``ThreadingHTTPServer`` (synchronous, thread-per-request);
asyncio queues require a running event loop and cannot be used from synchronous
threads without a dedicated wrapper.  ``queue.Queue`` integrates directly with
``ThreadingHTTPServer`` threads.

Queue-processor steps per item:

1. Validate the record dict against its JSON Schema.
2. Write to a ``.tmp`` file in the destination directory.
3. Re-validate the ``.tmp`` file against the schema.
4. Rename with ``os.replace()`` — MUST NOT use ``os.rename()`` (raises
   ``FileExistsError`` on Windows when the target exists).
5. Update the SQLite ``scr_index`` table in the same controller operation.

On any step failure: delete the ``.tmp`` if present, log the error, return a
:class:`WriteResult` with ``success=False``.  A partial ``.tmp`` is never
left on disk.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from helm_controller.contracts._jsonschema_lite import SchemaValidator, compile_schema
from helm_controller.scr import atomic_write as _aw
from helm_controller.scr.atomic_write import AtomicWriteError
from helm_controller.scr.identity import new_record_id
from helm_controller.scr.index import ScrIndex

_LOGGER = logging.getLogger(__name__)

_STOP_SENTINEL = object()

SCR_SCHEMA_VERSION = "1"

_RECORD_CLASS_TO_SCHEMA_STEM: dict[str, str] = {
    "approval": "scr-approval-record.schema.v1.json",
    "trace": "scr-trace-record.schema.v1.json",
    "runtime_memory": "scr-runtime-memory-record.schema.v1.json",
}

KNOWN_RECORD_CLASSES: frozenset[str] = frozenset(_RECORD_CLASS_TO_SCHEMA_STEM)


def _find_contracts_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "artifacts" / "contracts"
        if candidate.is_dir():
            return candidate
    raise RuntimeError(
        "ScrWriteQueue: could not locate artifacts/contracts directory"
    )


def _load_schema_map() -> dict[str, SchemaValidator]:
    contracts_dir = _find_contracts_dir()
    result: dict[str, SchemaValidator] = {}
    for record_class, stem in _RECORD_CLASS_TO_SCHEMA_STEM.items():
        path = contracts_dir / stem
        with path.open("r", encoding="utf-8") as fh:
            schema = json.load(fh)
        result[record_class] = compile_schema(schema)
    return result


@dataclass(frozen=True)
class WriteResult:
    success: bool
    record_id: str | None = None
    file_path: str | None = None
    error: str | None = None


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ScrWriteQueue:
    """Single-writer queue serializing all ``.scr/`` file commits.

    *scr_root* is the ``.scr/`` directory (``<workspace>/.scr``).
    *db_path* is the SQLite database shared with the runtime store.
    *schema_map* maps record-class names to their compiled validators; when
    ``None`` the map is loaded from ``artifacts/contracts/`` at construction
    time.
    """

    def __init__(
        self,
        scr_root: Path,
        db_path: Path,
        *,
        schema_map: dict[str, SchemaValidator] | None = None,
        busy_timeout_ms: int = 5000,
    ) -> None:
        self._scr_root = scr_root
        self._scr_root.mkdir(parents=True, exist_ok=True)
        self._schema_map: dict[str, SchemaValidator] = (
            schema_map if schema_map is not None else _load_schema_map()
        )
        self._index = ScrIndex(db_path, busy_timeout_ms=busy_timeout_ms)
        self._index.initialize()
        self._q: queue.Queue[Any] = queue.Queue()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the background worker thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._worker, name="scr-write-queue", daemon=True
        )
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the worker to stop and join within *timeout* seconds."""
        self._q.put(_STOP_SENTINEL)
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def submit(self, record: dict[str, Any]) -> WriteResult:
        """Enqueue *record* for writing and block until the result is ready.

        Auto-fills ``record_id``, ``created_at``, and ``scr_schema_version``
        if absent from the caller-supplied dict.
        """
        enriched = dict(record)
        if "record_id" not in enriched:
            enriched["record_id"] = new_record_id()
        if "created_at" not in enriched:
            enriched["created_at"] = _utcnow_iso()
        if "scr_schema_version" not in enriched:
            enriched["scr_schema_version"] = SCR_SCHEMA_VERSION

        resp: queue.Queue[WriteResult] = queue.Queue()
        self._q.put((enriched, resp))
        return resp.get()

    def _worker(self) -> None:
        while True:
            item = self._q.get(block=True)
            if item is _STOP_SENTINEL:
                self._q.task_done()
                break
            record, resp_queue = item
            try:
                result = self._process(record)
            except Exception as exc:
                _LOGGER.exception("SCR worker uncaught error")
                result = WriteResult(success=False, error=str(exc))
            resp_queue.put(result)
            self._q.task_done()

    def _process(self, record: dict[str, Any]) -> WriteResult:
        record_class = record.get("record_class", "")
        validator = self._schema_map.get(record_class)
        if validator is None:
            msg = f"unknown record_class {record_class!r}"
            _LOGGER.error("SCR write failure: %s", msg)
            return WriteResult(success=False, error=msg)

        workflow_id = record.get("workflow_id", "")
        record_id = record.get("record_id", "")
        if not workflow_id or not record_id:
            msg = "record missing workflow_id or record_id"
            _LOGGER.error("SCR write failure: %s", msg)
            return WriteResult(success=False, error=msg)

        dest_path = self._scr_root / record_class / workflow_id / f"{record_id}.json"

        try:
            _aw.write_record(dest_path, record, validator)
        except AtomicWriteError as exc:
            _LOGGER.error("SCR write failure: %s", exc)
            return WriteResult(success=False, error=str(exc))
        except Exception as exc:
            _LOGGER.exception("SCR write unexpected error")
            return WriteResult(success=False, error=str(exc))

        try:
            with self._index._connect() as conn:
                self._index.insert(conn, record, str(dest_path))
        except Exception as exc:
            _LOGGER.error("SCR index update failed (file committed): %s", exc)
            return WriteResult(success=False, error=f"index update failed: {exc}")

        return WriteResult(
            success=True,
            record_id=record_id,
            file_path=str(dest_path),
        )
