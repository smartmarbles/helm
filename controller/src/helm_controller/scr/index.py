"""SQLite-backed derived index for .scr/ records (spec015 Task 11.4).

The index is a *derived, rebuildable projection* — the ``.scr/`` JSON files
are authoritative.  :meth:`ScrIndex.rebuild` walks the ``.scr/`` tree and
reconstructs the index from scratch; it is idempotent.

Schema: ``scr_index(record_id, record_class, workflow_id, session_id,
turn_id, created_at, file_path)``.

Thread-safety: the same connection-per-operation pattern used by the Phase 2
``RuntimeStoreAdapter``.  Every public method opens a fresh connection, sets
WAL + busy_timeout + foreign_keys, and closes before returning.  The
:meth:`insert` method accepts an already-open connection so the write-queue
processor can wrap the file rename and index insert in the same SQLite
transaction context.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS scr_index (
    record_id    TEXT NOT NULL PRIMARY KEY,
    record_class TEXT NOT NULL,
    workflow_id  TEXT NOT NULL,
    session_id   TEXT NOT NULL,
    turn_id      TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    file_path    TEXT NOT NULL
);
"""

_INSERT_SQL = (
    "INSERT OR REPLACE INTO scr_index "
    "(record_id, record_class, workflow_id, session_id, turn_id, created_at, file_path) "
    "VALUES (?, ?, ?, ?, ?, ?, ?)"
)


@dataclass(frozen=True)
class ScrIndexRow:
    record_id: str
    record_class: str
    workflow_id: str
    session_id: str
    turn_id: str
    created_at: str
    file_path: str


class ScrIndexError(Exception):
    """Raised when an index operation cannot be completed."""


class ScrIndex:
    """Derived SQLite index over the ``.scr/`` record tree."""

    def __init__(self, db_path: Path, *, busy_timeout_ms: int = 5000) -> None:
        self._db_path = db_path
        self._busy_timeout_ms = busy_timeout_ms

    def initialize(self) -> None:
        """Create ``scr_index`` table if absent. Idempotent."""
        with self._connect() as conn:
            conn.executescript(_CREATE_TABLE_SQL)

    def insert(self, conn: sqlite3.Connection, record: dict[str, Any], file_path: str) -> None:
        """Insert a single index row using an already-open *conn*.

        Called by the write-queue processor within the same connection context
        as the file commit so the index update shares the same SQLite
        transaction.
        """
        conn.execute(
            _INSERT_SQL,
            (
                record["record_id"],
                record["record_class"],
                record["workflow_id"],
                record["session_id"],
                record["turn_id"],
                record["created_at"],
                file_path,
            ),
        )

    def query(self, record_id: str) -> ScrIndexRow | None:
        """Return the index row for *record_id*, or ``None`` if absent."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT record_id, record_class, workflow_id, session_id, "
                "turn_id, created_at, file_path FROM scr_index WHERE record_id = ?",
                (record_id,),
            ).fetchone()
        if row is None:
            return None
        return ScrIndexRow(
            record_id=row["record_id"],
            record_class=row["record_class"],
            workflow_id=row["workflow_id"],
            session_id=row["session_id"],
            turn_id=row["turn_id"],
            created_at=row["created_at"],
            file_path=row["file_path"],
        )

    def count(self) -> int:
        """Return the total number of rows in the index."""
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM scr_index").fetchone()
        return int(row[0])

    def rebuild(self, scr_root: Path) -> int:
        """Reconstruct the index from files under *scr_root*.

        Idempotent: clears the table and re-inserts one row per valid ``.json``
        file found recursively under *scr_root*.  Files that cannot be parsed
        or are missing required fields are skipped with a warning.

        Returns the number of records successfully indexed.
        """
        rows: list[tuple[str, ...]] = []
        for json_file in sorted(scr_root.rglob("*.json")):
            try:
                with json_file.open("r", encoding="utf-8") as fh:
                    record: dict[str, Any] = json.load(fh)
                rows.append(
                    (
                        str(record["record_id"]),
                        str(record["record_class"]),
                        str(record["workflow_id"]),
                        str(record["session_id"]),
                        str(record["turn_id"]),
                        str(record["created_at"]),
                        str(json_file),
                    )
                )
            except (OSError, json.JSONDecodeError, KeyError) as exc:
                _LOGGER.warning("REBUILD: skipping %s — %s", json_file, exc)

        with self._connect() as conn:
            conn.execute("DELETE FROM scr_index")
            conn.executemany(_INSERT_SQL, rows)

        return len(rows)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path, timeout=self._busy_timeout_ms / 1000.0)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(f"PRAGMA busy_timeout={self._busy_timeout_ms}")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute(_CREATE_TABLE_SQL)
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
