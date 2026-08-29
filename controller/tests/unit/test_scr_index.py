"""Unit tests for helm_controller.scr.index (spec015 Task 11.5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from helm_controller.scr.index import ScrIndex, ScrIndexRow


def _make_record(
    record_id: str = "r-001",
    record_class: str = "approval",
    workflow_id: str = "wf-abc",
    session_id: str = "sess-1",
    turn_id: str = "t-1",
    created_at: str = "2026-05-31T12:00:00+00:00",
) -> dict:
    return {
        "record_id": record_id,
        "record_class": record_class,
        "workflow_id": workflow_id,
        "session_id": session_id,
        "turn_id": turn_id,
        "created_at": created_at,
    }


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture()
def index(db_path: Path) -> ScrIndex:
    idx = ScrIndex(db_path)
    idx.initialize()
    return idx


class TestScrIndex:
    def test_initialize_idempotent(self, db_path: Path) -> None:
        idx = ScrIndex(db_path)
        idx.initialize()
        idx.initialize()
        assert db_path.exists()

    def test_insert_and_query(self, index: ScrIndex, db_path: Path) -> None:
        record = _make_record()
        with index._connect() as conn:
            index.insert(conn, record, "/fake/path/r-001.json")
        row = index.query("r-001")
        assert isinstance(row, ScrIndexRow)
        assert row.record_id == "r-001"
        assert row.record_class == "approval"
        assert row.workflow_id == "wf-abc"
        assert row.file_path == "/fake/path/r-001.json"

    def test_query_missing_record_returns_none(self, index: ScrIndex) -> None:
        assert index.query("does-not-exist") is None

    def test_count_empty(self, index: ScrIndex) -> None:
        assert index.count() == 0

    def test_count_after_inserts(self, index: ScrIndex) -> None:
        for i in range(3):
            record = _make_record(record_id=f"r-{i:03d}")
            with index._connect() as conn:
                index.insert(conn, record, f"/path/r-{i:03d}.json")
        assert index.count() == 3

    def test_rebuild_empty_scr_root(self, index: ScrIndex, tmp_path: Path) -> None:
        scr_root = tmp_path / ".scr"
        scr_root.mkdir()
        n = index.rebuild(scr_root)
        assert n == 0
        assert index.count() == 0

    def test_rebuild_populates_index(self, index: ScrIndex, tmp_path: Path) -> None:
        scr_root = tmp_path / ".scr"
        for i in range(3):
            record = _make_record(record_id=f"r-{i:03d}")
            dest = scr_root / "approval" / "wf-abc" / f"r-{i:03d}.json"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(record), encoding="utf-8")

        n = index.rebuild(scr_root)
        assert n == 3
        assert index.count() == 3

    def test_rebuild_idempotency(self, index: ScrIndex, tmp_path: Path) -> None:
        scr_root = tmp_path / ".scr"
        for i in range(4):
            record = _make_record(record_id=f"r-{i:03d}")
            dest = scr_root / "approval" / "wf-abc" / f"r-{i:03d}.json"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(record), encoding="utf-8")

        n1 = index.rebuild(scr_root)
        count1 = index.count()
        n2 = index.rebuild(scr_root)
        count2 = index.count()

        assert n1 == n2 == 4
        assert count1 == count2 == 4

    def test_rebuild_skips_malformed_json(self, index: ScrIndex, tmp_path: Path) -> None:
        scr_root = tmp_path / ".scr"
        good = scr_root / "approval" / "wf-abc" / "good.json"
        good.parent.mkdir(parents=True, exist_ok=True)
        good.write_text(json.dumps(_make_record(record_id="good")), encoding="utf-8")
        bad = scr_root / "approval" / "wf-abc" / "bad.json"
        bad.write_text("{NOT JSON", encoding="utf-8")

        n = index.rebuild(scr_root)
        assert n == 1
        assert index.count() == 1

    def test_rebuild_skips_missing_fields(self, index: ScrIndex, tmp_path: Path) -> None:
        scr_root = tmp_path / ".scr"
        dest = scr_root / "approval" / "wf-abc" / "no_id.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps({"only": "partial"}), encoding="utf-8")
        n = index.rebuild(scr_root)
        assert n == 0

    def test_rebuild_clears_stale_rows(self, index: ScrIndex, tmp_path: Path) -> None:
        record = _make_record(record_id="r-stale")
        with index._connect() as conn:
            index.insert(conn, record, "/stale/path.json")
        assert index.count() == 1

        scr_root = tmp_path / ".scr"
        scr_root.mkdir()
        index.rebuild(scr_root)
        assert index.count() == 0

    def test_insert_or_replace_on_duplicate(self, index: ScrIndex) -> None:
        record = _make_record()
        with index._connect() as conn:
            index.insert(conn, record, "/path/v1.json")
        with index._connect() as conn:
            index.insert(conn, record, "/path/v2.json")
        row = index.query("r-001")
        assert row is not None
        assert row.file_path == "/path/v2.json"
        assert index.count() == 1

    def test_connect_rollback_on_exception(self, index: ScrIndex) -> None:
        import sqlite3 as _sqlite3
        with pytest.raises(_sqlite3.OperationalError):
            with index._connect() as conn:
                conn.execute("SELECT * FROM nonexistent_table_xyz")
        assert index.count() == 0
