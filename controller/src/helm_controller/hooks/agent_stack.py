"""Per-``sessionId`` active-agent stack + session-routing tier (spec015 Task 3.2).

``PreToolUse``/``PostToolUse`` payloads carry no agent identity (Watch Out #2),
so ``actor.active_agent`` must be derived from a stack maintained across the
``SubagentStart`` (push) / ``SubagentStop`` (pop) lifecycle events. The base of
the stack — an empty stack — is the root orchestrator session (ARTHUR); the top
of a non-empty stack is the subagent currently executing.

Persistence shape (resolves a plan ambiguity — see the closeout note). Task 2.1
``schema.sql`` deliberately omitted the *session-scoped routing* tier
("``session_active_workflow_id`` ... a separate tier and is intentionally
omitted") from the *workflow-scoped persistent* tier. Task 3.2 / Watch Out #2
require the stack survive a controller restart, so this module owns that
separate routing tier in the SAME runtime database file the workflow store uses
— it is NOT a parallel store. Two tables are created idempotently on init:

* ``agent_stack`` — one row per pushed subagent, keyed ``(session_id, depth)``;
  the top of the stack is the row with the greatest ``depth``.
* ``session_state`` — one row per session holding the monotonic ``turn_counter``
  (incremented on each ``UserPromptSubmit``; Watch Out #18) and the
  ``active_workflow_id`` routing pointer the envelope assembler resolves the
  workflow-scoped identity through.

Thread-safety follows the adapter's pattern (a): a fresh connection per public
operation, never crossing a thread boundary, with ``PRAGMA journal_mode=WAL`` so
``http.server.ThreadingHTTPServer`` (Task 3.0) can dispatch concurrent sessions'
hook events without lock starvation. Per-session isolation is the
``(session_id, …)`` key prefix on every table.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

_CREATE_AGENT_STACK = """
CREATE TABLE IF NOT EXISTS agent_stack (
    session_id  TEXT    NOT NULL,
    depth       INTEGER NOT NULL,
    agent_type  TEXT    NOT NULL,
    subagent_id TEXT,
    pushed_at   TEXT    NOT NULL,
    PRIMARY KEY (session_id, depth)
)
"""

_CREATE_SESSION_STATE = """
CREATE TABLE IF NOT EXISTS session_state (
    session_id          TEXT    NOT NULL PRIMARY KEY,
    active_workflow_id  TEXT,
    turn_counter        INTEGER NOT NULL DEFAULT 0,
    updated_at          TEXT    NOT NULL
)
"""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class AgentFrame:
    """One pushed subagent on a session's active-agent stack."""

    session_id: str
    depth: int
    agent_type: str
    subagent_id: str | None
    pushed_at: str


class AgentStackStore:
    """SQLite-backed per-session active-agent stack + routing pointers."""

    def __init__(
        self,
        db_path: Path,
        *,
        busy_timeout_ms: int = 5000,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._db_path = db_path
        self._busy_timeout_ms = busy_timeout_ms
        self._clock = clock
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(_CREATE_AGENT_STACK)
            conn.execute(_CREATE_SESSION_STATE)

    @classmethod
    def from_db_path(
        cls,
        db_path: Path,
        *,
        busy_timeout_ms: int = 5000,
        clock: Callable[[], datetime] = _utcnow,
    ) -> "AgentStackStore":
        return cls(db_path, busy_timeout_ms=busy_timeout_ms, clock=clock)

    # ---- stack operations ------------------------------------------------- #
    def push(
        self, session_id: str, agent_type: str, *, subagent_id: str | None = None
    ) -> AgentFrame:
        """Push a subagent onto ``session_id``'s stack; the new frame is the top."""
        pushed_at = self._now_iso()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(depth), 0) + 1 AS next FROM agent_stack "
                "WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            depth = int(row["next"])
            conn.execute(
                "INSERT INTO agent_stack "
                "(session_id, depth, agent_type, subagent_id, pushed_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (session_id, depth, agent_type, subagent_id, pushed_at),
            )
        return AgentFrame(session_id, depth, agent_type, subagent_id, pushed_at)

    def pop(self, session_id: str) -> AgentFrame | None:
        """Pop the top frame. Returns ``None`` on an empty/unknown session stack."""
        with self._connect() as conn:
            record = conn.execute(
                "SELECT session_id, depth, agent_type, subagent_id, pushed_at "
                "FROM agent_stack WHERE session_id = ? "
                "ORDER BY depth DESC LIMIT 1",
                (session_id,),
            ).fetchone()
            if record is None:
                return None
            conn.execute(
                "DELETE FROM agent_stack WHERE session_id = ? AND depth = ?",
                (session_id, record["depth"]),
            )
        return self._frame(record)

    def current(self, session_id: str) -> AgentFrame | None:
        """Return the top frame without mutating; ``None`` when the stack is empty."""
        with self._connect() as conn:
            record = conn.execute(
                "SELECT session_id, depth, agent_type, subagent_id, pushed_at "
                "FROM agent_stack WHERE session_id = ? "
                "ORDER BY depth DESC LIMIT 1",
                (session_id,),
            ).fetchone()
        if record is None:
            return None
        return self._frame(record)

    def depth(self, session_id: str) -> int:
        """Return the number of pushed subagents for ``session_id`` (0 = root)."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM agent_stack WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return int(row["n"])

    # ---- session-routing tier --------------------------------------------- #
    def current_turn(self, session_id: str) -> int:
        """Return the current ``turn_counter`` (0 when no prompt has fired yet)."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT turn_counter FROM session_state WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return 0
        return int(row["turn_counter"])

    def increment_turn(self, session_id: str) -> int:
        """Increment and return ``turn_counter`` (called on ``UserPromptSubmit``)."""
        now = self._now_iso()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO session_state "
                "(session_id, active_workflow_id, turn_counter, updated_at) "
                "VALUES (?, NULL, 1, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET "
                "turn_counter = turn_counter + 1, updated_at = excluded.updated_at",
                (session_id, now),
            )
            row = conn.execute(
                "SELECT turn_counter FROM session_state WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return int(row["turn_counter"])

    def active_workflow_id(self, session_id: str) -> str | None:
        """Return the session's active-workflow routing pointer, or ``None``."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT active_workflow_id FROM session_state WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return row["active_workflow_id"]

    def set_active_workflow(
        self, session_id: str, workflow_id: str | None
    ) -> None:
        """Set (or clear, with ``None``) the session's active-workflow pointer."""
        now = self._now_iso()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO session_state "
                "(session_id, active_workflow_id, turn_counter, updated_at) "
                "VALUES (?, ?, 0, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET "
                "active_workflow_id = excluded.active_workflow_id, "
                "updated_at = excluded.updated_at",
                (session_id, workflow_id, now),
            )

    # ---- internals -------------------------------------------------------- #
    @staticmethod
    def _frame(record: sqlite3.Row) -> AgentFrame:
        return AgentFrame(
            session_id=record["session_id"],
            depth=int(record["depth"]),
            agent_type=record["agent_type"],
            subagent_id=record["subagent_id"],
            pushed_at=record["pushed_at"],
        )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(
            self._db_path, timeout=self._busy_timeout_ms / 1000.0
        )
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(f"PRAGMA busy_timeout={self._busy_timeout_ms}")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _now_iso(self) -> str:
        return self._clock().strftime("%Y-%m-%dT%H:%M:%SZ")
