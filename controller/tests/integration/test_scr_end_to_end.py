"""Integration tests for the SCR write path (spec015 Task 11.5).

Covers:
- Valid approval round-trip: write → index read → file matches schema.
- Atomic-write crash simulation: os.replace() fails → no .tmp residue, no
  corrupt file, REBUILD produces consistent index.
- .scr/ direct-write via file_mutation denied with PC-003 (Phase 4 matrix).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from helm_controller.contracts._jsonschema_lite import compile_schema
from helm_controller.scr.index import ScrIndex
from helm_controller.scr.write_queue import ScrWriteQueue


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

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
        "record_id": "r-e2e-001",
        "workflow_id": "wf-e2e",
        "session_id": "sess-e2e",
        "turn_id": "t-e2e",
        "created_at": "2026-05-31T12:00:00+00:00",
        "approved_by": "ARTHUR",
        "decision": "allow",
        "tool_name": "create_file",
        "tool_use_id": "tu-e2e",
    }
    base.update(overrides)
    return base


@pytest.fixture()
def schema_map() -> dict:
    return {"approval": compile_schema(_APPROVAL_SCHEMA)}


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    return tmp_path / "workspace"


@pytest.fixture()
def scr_root(workspace: Path) -> Path:
    return workspace / ".scr"


@pytest.fixture()
def db_path(workspace: Path) -> Path:
    return workspace / ".helm-controller.db"


@pytest.fixture()
def queue_instance(
    scr_root: Path, db_path: Path, schema_map: dict
) -> ScrWriteQueue:
    q = ScrWriteQueue(
        scr_root=scr_root,
        db_path=db_path,
        schema_map=schema_map,
    )
    q.start()
    yield q
    q.stop()


# ---------------------------------------------------------------------------
# Test 1: valid approval round-trip
# ---------------------------------------------------------------------------


class TestApprovalRoundTrip:
    def test_write_index_file_consistent(
        self,
        queue_instance: ScrWriteQueue,
        scr_root: Path,
        db_path: Path,
        schema_map: dict,
    ) -> None:
        record = _approval_record()
        result = queue_instance.submit(record)

        assert result.success, result.error

        index = ScrIndex(db_path)
        row = index.query("r-e2e-001")
        assert row is not None
        assert row.record_class == "approval"
        assert row.workflow_id == "wf-e2e"

        file_content = json.loads(Path(row.file_path).read_bytes())
        validator = schema_map["approval"]
        errors = validator.collect(file_content)
        assert errors == [], f"file fails schema: {errors}"
        assert file_content["record_id"] == "r-e2e-001"
        assert file_content["decision"] == "allow"


# ---------------------------------------------------------------------------
# Test 2: atomic-write crash simulation
# ---------------------------------------------------------------------------


class TestAtomicWriteCrashSimulation:
    def test_crash_before_replace_leaves_no_corruption(
        self,
        queue_instance: ScrWriteQueue,
        scr_root: Path,
        db_path: Path,
    ) -> None:
        record = _approval_record(record_id="r-crash")

        with patch(
            "helm_controller.scr.atomic_write.os.replace",
            side_effect=OSError("simulated process kill"),
        ):
            result = queue_instance.submit(record)

        assert not result.success

        all_tmp = list(scr_root.rglob("*.tmp"))
        assert all_tmp == [], f".tmp files found after crash: {all_tmp}"

        dest = scr_root / "approval" / "wf-e2e" / "r-crash.json"
        assert not dest.exists(), "corrupt .scr/ file found after crash"

    def test_rebuild_consistent_after_crash(
        self,
        queue_instance: ScrWriteQueue,
        scr_root: Path,
        db_path: Path,
    ) -> None:
        record_committed = _approval_record(record_id="r-committed")
        good_result = queue_instance.submit(record_committed)
        assert good_result.success

        with patch(
            "helm_controller.scr.atomic_write.os.replace",
            side_effect=OSError("crash"),
        ):
            queue_instance.submit(_approval_record(record_id="r-crashed"))

        index = ScrIndex(db_path)
        n = index.rebuild(scr_root)
        assert n == 1
        assert index.count() == 1
        row = index.query("r-committed")
        assert row is not None

    def test_rebuild_idempotent_after_crash(
        self,
        queue_instance: ScrWriteQueue,
        scr_root: Path,
        db_path: Path,
    ) -> None:
        queue_instance.submit(_approval_record(record_id="r-idem-1"))
        queue_instance.submit(_approval_record(record_id="r-idem-2"))

        index = ScrIndex(db_path)
        count_a = index.rebuild(scr_root)
        count_b = index.rebuild(scr_root)

        assert count_a == count_b == 2
        assert index.count() == 2


# ---------------------------------------------------------------------------
# Test 3: .scr/ direct-write denied with PC-003 (Phase 4 integration)
# ---------------------------------------------------------------------------


class TestScrPathDeniedByPhase4:
    def test_file_mutation_into_scr_denied_pc003(self, tmp_path: Path) -> None:
        import json as _json

        from helm_controller.policy.conditional_checks import (
            PC_003,
            check_scr_path,
        )
        from helm_controller.policy.tool_classes import ToolClassMap

        workspace = str(tmp_path)
        tcm_data = {
            "version": "1.0",
            "classes": {
                "file_mutation": [
                    {"name": "create_file", "path_fields": ["filePath"]},
                ],
                "agent_dispatch": [],
            },
        }
        tcm_path = tmp_path / "tc.json"
        tcm_path.write_text(_json.dumps(tcm_data), encoding="utf-8")
        tcm = ToolClassMap(tcm_path)

        scr_target = str(tmp_path / ".scr" / "approval" / "wf-1" / "rec.json")
        result = check_scr_path(
            "create_file",
            {"filePath": scr_target},
            workspace,
            tcm,
        )

        assert not result.passed
        assert result.reason_id == PC_003

    def test_file_mutation_outside_scr_allowed(self, tmp_path: Path) -> None:
        import json as _json

        from helm_controller.policy.conditional_checks import check_scr_path
        from helm_controller.policy.tool_classes import ToolClassMap

        workspace = str(tmp_path)
        tcm_data = {
            "version": "1.0",
            "classes": {
                "file_mutation": [
                    {"name": "create_file", "path_fields": ["filePath"]},
                ],
                "agent_dispatch": [],
            },
        }
        tcm_path = tmp_path / "tc.json"
        tcm_path.write_text(_json.dumps(tcm_data), encoding="utf-8")
        tcm = ToolClassMap(tcm_path)

        safe_target = str(tmp_path / "artifacts" / "some_file.md")
        result = check_scr_path(
            "create_file",
            {"filePath": safe_target},
            workspace,
            tcm,
        )

        assert result.passed
