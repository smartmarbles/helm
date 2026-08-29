"""Unit tests for helm_controller.scr.write_queue (spec015 Task 11.5)."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from helm_controller.contracts._jsonschema_lite import compile_schema
from helm_controller.scr.write_queue import ScrWriteQueue, WriteResult

_APPROVAL_SCHEMA = {
    "type": "object",
    "required": [
        "scr_schema_version",
        "record_class",
        "record_id",
        "workflow_id",
        "session_id",
        "turn_id",
        "created_at",
        "approved_by",
        "decision",
        "tool_name",
        "tool_use_id",
    ],
    "additionalProperties": False,
    "properties": {
        "scr_schema_version": {"type": "string", "const": "1"},
        "record_class": {"type": "string", "const": "approval"},
        "record_id": {"type": "string", "minLength": 1},
        "workflow_id": {"type": "string", "minLength": 1},
        "session_id": {"type": "string", "minLength": 1},
        "turn_id": {"type": "string", "minLength": 1},
        "created_at": {"type": "string", "minLength": 1},
        "approved_by": {"type": "string", "minLength": 1},
        "decision": {"type": "string", "enum": ["allow", "deny", "ask"]},
        "tool_name": {"type": "string", "minLength": 1},
        "tool_use_id": {"type": "string", "minLength": 1},
    },
}


def _approval_record(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "scr_schema_version": "1",
        "record_class": "approval",
        "record_id": "r-001",
        "workflow_id": "wf-abc",
        "session_id": "sess-1",
        "turn_id": "t-1",
        "created_at": "2026-05-31T12:00:00+00:00",
        "approved_by": "ARTHUR",
        "decision": "allow",
        "tool_name": "create_file",
        "tool_use_id": "tu-001",
    }
    base.update(overrides)
    return base


@pytest.fixture()
def schema_map() -> dict:
    return {"approval": compile_schema(_APPROVAL_SCHEMA)}


@pytest.fixture()
def queue_instance(tmp_path: Path, schema_map: dict) -> ScrWriteQueue:
    q = ScrWriteQueue(
        scr_root=tmp_path / ".scr",
        db_path=tmp_path / ".helm-controller.db",
        schema_map=schema_map,
    )
    q.start()
    yield q
    q.stop()


class TestScrWriteQueue:
    def test_valid_record_round_trip(
        self, queue_instance: ScrWriteQueue, tmp_path: Path
    ) -> None:
        record = _approval_record()
        result = queue_instance.submit(record)
        assert result.success
        assert result.record_id == "r-001"
        written = json.loads(Path(result.file_path).read_bytes())
        assert written["record_id"] == "r-001"
        assert written["decision"] == "allow"

    def test_file_at_expected_path(
        self, queue_instance: ScrWriteQueue, tmp_path: Path
    ) -> None:
        record = _approval_record(record_id="r-path")
        result = queue_instance.submit(record)
        assert result.success
        expected = tmp_path / ".scr" / "approval" / "wf-abc" / "r-path.json"
        assert expected.exists()

    def test_schema_reject_returns_failure(
        self, queue_instance: ScrWriteQueue
    ) -> None:
        bad = _approval_record(decision="INVALID_DECISION")
        result = queue_instance.submit(bad)
        assert not result.success
        assert result.error is not None

    def test_schema_reject_no_tmp_residue(
        self, queue_instance: ScrWriteQueue, tmp_path: Path
    ) -> None:
        bad = _approval_record(decision="INVALID_DECISION")
        queue_instance.submit(bad)
        tmp_files = list((tmp_path / ".scr").rglob("*.tmp"))
        assert tmp_files == []

    def test_unknown_record_class_returns_failure(
        self, queue_instance: ScrWriteQueue
    ) -> None:
        record = _approval_record(record_class="nonexistent")
        result = queue_instance.submit(record)
        assert not result.success

    def test_concurrent_writes_same_workflow_no_collision(
        self, queue_instance: ScrWriteQueue, tmp_path: Path
    ) -> None:
        results: list[WriteResult] = [None, None]  # type: ignore[list-item]

        def _submit(index: int, record_id: str) -> None:
            results[index] = queue_instance.submit(
                _approval_record(record_id=record_id, tool_use_id=f"tu-{index}")
            )

        t0 = threading.Thread(target=_submit, args=(0, "r-conc-0"))
        t1 = threading.Thread(target=_submit, args=(1, "r-conc-1"))
        t0.start()
        t1.start()
        t0.join()
        t1.join()

        assert results[0].success
        assert results[1].success
        assert results[0].record_id != results[1].record_id
        path0 = tmp_path / ".scr" / "approval" / "wf-abc" / "r-conc-0.json"
        path1 = tmp_path / ".scr" / "approval" / "wf-abc" / "r-conc-1.json"
        assert path0.exists()
        assert path1.exists()

    def test_auto_fills_record_id_if_absent(
        self, queue_instance: ScrWriteQueue
    ) -> None:
        record = _approval_record()
        del record["record_id"]
        result = queue_instance.submit(record)
        assert result.success
        assert result.record_id is not None and len(result.record_id) > 0

    def test_auto_fills_created_at_if_absent(
        self, queue_instance: ScrWriteQueue, tmp_path: Path
    ) -> None:
        record = _approval_record(record_id="r-date")
        del record["created_at"]
        result = queue_instance.submit(record)
        assert result.success
        written = json.loads(Path(result.file_path).read_bytes())
        assert written.get("created_at")

    def test_auto_fills_scr_schema_version_if_absent(
        self, queue_instance: ScrWriteQueue, tmp_path: Path
    ) -> None:
        record = _approval_record(record_id="r-ver")
        del record["scr_schema_version"]
        result = queue_instance.submit(record)
        assert result.success
        written = json.loads(Path(result.file_path).read_bytes())
        assert written["scr_schema_version"] == "1"

    def test_stop_exits_cleanly(self, tmp_path: Path, schema_map: dict) -> None:
        q = ScrWriteQueue(
            scr_root=tmp_path / ".scr",
            db_path=tmp_path / ".helm-controller.db",
            schema_map=schema_map,
        )
        q.start()
        assert q._thread is not None and q._thread.is_alive()
        q.stop(timeout=2.0)
        assert not q._thread.is_alive()

    def test_scr_root_created_on_init(self, tmp_path: Path, schema_map: dict) -> None:
        scr_root = tmp_path / "new_workspace" / ".scr"
        assert not scr_root.exists()
        ScrWriteQueue(
            scr_root=scr_root,
            db_path=tmp_path / "db",
            schema_map=schema_map,
        )
        assert scr_root.exists()

    def test_start_twice_does_not_spawn_second_thread(
        self, tmp_path: Path, schema_map: dict
    ) -> None:
        q = ScrWriteQueue(
            scr_root=tmp_path / ".scr",
            db_path=tmp_path / "db",
            schema_map=schema_map,
        )
        q.start()
        thread_id_first = id(q._thread)
        q.start()
        assert id(q._thread) == thread_id_first
        q.stop()

    def test_worker_catches_uncaught_exception(
        self, queue_instance: ScrWriteQueue
    ) -> None:
        from unittest.mock import patch as _patch
        from helm_controller.scr import write_queue as _wq_mod

        with _patch.object(queue_instance, "_process", side_effect=RuntimeError("boom")):
            result = queue_instance.submit(_approval_record())
        assert not result.success
        assert "boom" in result.error

    def test_index_update_failure_returns_error(
        self, queue_instance: ScrWriteQueue, tmp_path: Path
    ) -> None:
        from unittest.mock import patch as _patch
        from helm_controller.scr import index as _idx_mod

        with _patch.object(
            queue_instance._index,
            "_connect",
            side_effect=Exception("db crash"),
        ):
            result = queue_instance.submit(_approval_record(record_id="r-idxfail"))
        assert not result.success
        assert "index update failed" in result.error

    def test_load_schema_map_from_contracts_dir(self, tmp_path: Path) -> None:
        q = ScrWriteQueue(
            scr_root=tmp_path / ".scr",
            db_path=tmp_path / "db",
        )
        assert "approval" in q._schema_map
        assert "trace" in q._schema_map
        assert "runtime_memory" in q._schema_map

    def test_stop_before_start_does_not_error(
        self, tmp_path: Path, schema_map: dict
    ) -> None:
        q = ScrWriteQueue(
            scr_root=tmp_path / ".scr",
            db_path=tmp_path / "db",
            schema_map=schema_map,
        )
        q.stop(timeout=1.0)

    def test_find_contracts_dir_raises_when_not_found(self, tmp_path: Path) -> None:
        from pathlib import Path as _Path
        _real_is_dir = _Path.is_dir

        def _mock_is_dir(self_path: _Path) -> bool:
            if "artifacts" in str(self_path) and "contracts" in str(self_path):
                return False
            return _real_is_dir(self_path)

        with patch.object(_Path, "is_dir", _mock_is_dir):
            with pytest.raises(RuntimeError, match="could not locate"):
                ScrWriteQueue(
                    scr_root=tmp_path / ".scr",
                    db_path=tmp_path / "db",
                )
