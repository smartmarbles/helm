"""Tests for the per-session active-agent stack + routing tier (spec015 Task 3.2)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from helm_controller.hooks.agent_stack import AgentFrame, AgentStackStore


def _store(tmp_path: Path, **kwargs) -> AgentStackStore:
    return AgentStackStore(tmp_path / "store.db", **kwargs)


# --------------------------------------------------------------------------- #
# construction
# --------------------------------------------------------------------------- #
def test_init_creates_tables_and_parent_dir(tmp_path: Path) -> None:
    nested = tmp_path / "deep" / "store.db"
    store = AgentStackStore(nested)
    assert nested.is_file()
    assert store.depth("s") == 0


def test_from_db_path_classmethod(tmp_path: Path) -> None:
    store = AgentStackStore.from_db_path(tmp_path / "store.db", busy_timeout_ms=1234)
    assert store.depth("s") == 0


# --------------------------------------------------------------------------- #
# push / current / depth
# --------------------------------------------------------------------------- #
def test_push_assigns_ascending_depth(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = store.push("s", "SAGE", subagent_id="sub-1")
    second = store.push("s", "FORGE", subagent_id="sub-2")
    assert isinstance(first, AgentFrame)
    assert first.depth == 1
    assert second.depth == 2
    assert store.depth("s") == 2


def test_current_returns_top_of_stack(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.push("s", "SAGE")
    store.push("s", "FORGE", subagent_id="sub-2")
    top = store.current("s")
    assert top is not None
    assert top.agent_type == "FORGE"
    assert top.subagent_id == "sub-2"


def test_current_empty_stack_returns_none(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.current("unknown-session") is None
    assert store.depth("unknown-session") == 0


def test_push_records_pushed_at_from_clock(tmp_path: Path) -> None:
    fixed = datetime(2026, 5, 31, 12, 0, 0, tzinfo=timezone.utc)
    store = _store(tmp_path, clock=lambda: fixed)
    frame = store.push("s", "SAGE")
    assert frame.pushed_at == "2026-05-31T12:00:00Z"


# --------------------------------------------------------------------------- #
# pop / balance edge cases
# --------------------------------------------------------------------------- #
def test_pop_returns_and_removes_top(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.push("s", "SAGE")
    store.push("s", "FORGE")
    popped = store.pop("s")
    assert popped is not None
    assert popped.agent_type == "FORGE"
    assert store.depth("s") == 1
    assert store.current("s").agent_type == "SAGE"


def test_pop_empty_stack_returns_none(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.pop("s") is None


def test_unbalanced_pops_drain_to_empty(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.push("s", "SAGE")
    assert store.pop("s") is not None
    # Extra (unbalanced) pops are no-ops, never raise.
    assert store.pop("s") is None
    assert store.pop("s") is None
    assert store.depth("s") == 0


# --------------------------------------------------------------------------- #
# concurrent / isolated sessions
# --------------------------------------------------------------------------- #
def test_sessions_are_isolated(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.push("session-a", "SAGE")
    store.push("session-b", "FORGE")
    store.push("session-b", "QUILL")
    assert store.depth("session-a") == 1
    assert store.depth("session-b") == 2
    assert store.current("session-a").agent_type == "SAGE"
    assert store.current("session-b").agent_type == "QUILL"
    store.pop("session-b")
    assert store.current("session-b").agent_type == "FORGE"
    assert store.current("session-a").agent_type == "SAGE"


# --------------------------------------------------------------------------- #
# turn counter
# --------------------------------------------------------------------------- #
def test_current_turn_defaults_to_zero(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.current_turn("s") == 0


def test_increment_turn_is_monotonic(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.increment_turn("s") == 1
    assert store.increment_turn("s") == 2
    assert store.current_turn("s") == 2


def test_increment_turn_isolated_per_session(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.increment_turn("a")
    store.increment_turn("a")
    store.increment_turn("b")
    assert store.current_turn("a") == 2
    assert store.current_turn("b") == 1


# --------------------------------------------------------------------------- #
# active-workflow routing pointer
# --------------------------------------------------------------------------- #
def test_active_workflow_defaults_to_none(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.active_workflow_id("s") is None


def test_set_active_workflow_inserts_then_updates(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.set_active_workflow("s", "wf-1")
    assert store.active_workflow_id("s") == "wf-1"
    store.set_active_workflow("s", "wf-2")
    assert store.active_workflow_id("s") == "wf-2"


def test_set_active_workflow_can_clear_to_none(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.set_active_workflow("s", "wf-1")
    store.set_active_workflow("s", None)
    assert store.active_workflow_id("s") is None


def test_turn_and_active_workflow_coexist(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.increment_turn("s")
    store.set_active_workflow("s", "wf-1")
    assert store.current_turn("s") == 1
    assert store.active_workflow_id("s") == "wf-1"
    store.increment_turn("s")
    assert store.current_turn("s") == 2
    assert store.active_workflow_id("s") == "wf-1"


# --------------------------------------------------------------------------- #
# connection rollback path
# --------------------------------------------------------------------------- #
def test_push_null_agent_type_rolls_back_and_raises(tmp_path: Path) -> None:
    import sqlite3

    store = _store(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        store.push("s", None)  # type: ignore[arg-type]
    # Rollback left the stack empty — the failed INSERT was not committed.
    assert store.depth("s") == 0
