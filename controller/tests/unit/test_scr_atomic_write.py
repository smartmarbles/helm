"""Unit tests for helm_controller.scr.atomic_write (spec015 Task 11.5)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from helm_controller.contracts._jsonschema_lite import SchemaValidator, compile_schema
from helm_controller.scr.atomic_write import AtomicWriteError, write_record

_APPROVAL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["record_class", "record_id", "value"],
    "additionalProperties": False,
    "properties": {
        "record_class": {"type": "string"},
        "record_id": {"type": "string", "minLength": 1},
        "value": {"type": "string"},
    },
}


@pytest.fixture()
def validator() -> SchemaValidator:
    return compile_schema(_APPROVAL_SCHEMA)


@pytest.fixture()
def valid_record() -> dict[str, Any]:
    return {"record_class": "approval", "record_id": "r-001", "value": "ok"}


class TestWriteRecord:
    def test_valid_record_writes_file(
        self, tmp_path: Path, validator: SchemaValidator, valid_record: dict[str, Any]
    ) -> None:
        dest = tmp_path / "approval" / "wf-1" / "r-001.json"
        write_record(dest, valid_record, validator)
        assert dest.exists()
        assert json.loads(dest.read_bytes()) == valid_record

    def test_valid_record_no_tmp_residue(
        self, tmp_path: Path, validator: SchemaValidator, valid_record: dict[str, Any]
    ) -> None:
        dest = tmp_path / "r-001.json"
        write_record(dest, valid_record, validator)
        assert not (tmp_path / "r-001.json.tmp").exists()

    def test_creates_parent_directories(
        self, tmp_path: Path, validator: SchemaValidator, valid_record: dict[str, Any]
    ) -> None:
        dest = tmp_path / "a" / "b" / "c" / "rec.json"
        assert not dest.parent.exists()
        write_record(dest, valid_record, validator)
        assert dest.exists()

    def test_schema_reject_raises_atomic_write_error(
        self, tmp_path: Path, validator: SchemaValidator
    ) -> None:
        bad = {"record_class": "approval", "record_id": "", "value": "x"}
        dest = tmp_path / "bad.json"
        with pytest.raises(AtomicWriteError, match="pre-write validation failed"):
            write_record(dest, bad, validator)

    def test_schema_reject_leaves_no_tmp(
        self, tmp_path: Path, validator: SchemaValidator
    ) -> None:
        bad = {"record_class": "approval", "record_id": "", "value": "x"}
        dest = tmp_path / "bad.json"
        with pytest.raises(AtomicWriteError):
            write_record(dest, bad, validator)
        assert not (tmp_path / "bad.json.tmp").exists()
        assert not dest.exists()

    def test_schema_reject_missing_required(
        self, tmp_path: Path, validator: SchemaValidator
    ) -> None:
        bad = {"record_class": "approval", "value": "missing record_id"}
        dest = tmp_path / "bad2.json"
        with pytest.raises(AtomicWriteError):
            write_record(dest, bad, validator)

    def test_os_replace_called_not_os_rename(
        self, tmp_path: Path, validator: SchemaValidator, valid_record: dict[str, Any]
    ) -> None:
        import inspect
        import helm_controller.scr.atomic_write as _mod

        dest = tmp_path / "r-001.json"
        _real_replace = os.replace
        with patch("helm_controller.scr.atomic_write.os.replace") as mock_replace:
            mock_replace.side_effect = _real_replace
            write_record(dest, valid_record, validator)
        mock_replace.assert_called_once()

        func_src = inspect.getsource(_mod.write_record)
        assert "os.replace(" in func_src, "write_record must call os.replace()"
        assert "os.rename(" not in func_src, "write_record must not call os.rename()"

    def test_replace_failure_cleans_tmp(
        self, tmp_path: Path, validator: SchemaValidator, valid_record: dict[str, Any]
    ) -> None:
        dest = tmp_path / "r-001.json"
        tmp_path2 = dest.parent / (dest.name + ".tmp")
        with patch(
            "helm_controller.scr.atomic_write.os.replace",
            side_effect=OSError("simulated crash"),
        ):
            with pytest.raises((AtomicWriteError, OSError)):
                write_record(dest, valid_record, validator)
        assert not tmp_path2.exists()
        assert not dest.exists()

    def test_post_write_validation_failure_cleans_tmp(
        self, tmp_path: Path, validator: SchemaValidator, valid_record: dict[str, Any]
    ) -> None:
        dest = tmp_path / "r-001.json"
        invalid_json_bytes = b'{"record_class": "approval", "record_id": "", "value": "x"}'

        original_write_bytes = Path.write_bytes

        def _bad_write(self_path: Path, data: bytes) -> int:
            return original_write_bytes(self_path, invalid_json_bytes)

        with patch.object(Path, "write_bytes", _bad_write):
            with pytest.raises(AtomicWriteError):
                write_record(dest, valid_record, validator)

        tmp_file = dest.parent / (dest.name + ".tmp")
        assert not tmp_file.exists()
        assert not dest.exists()

    def test_write_bytes_oserror_raises_atomic_write_error(
        self, tmp_path: Path, validator: SchemaValidator, valid_record: dict[str, Any]
    ) -> None:
        dest = tmp_path / "r-001.json"
        with patch.object(Path, "write_bytes", side_effect=OSError("disk full")):
            with pytest.raises(AtomicWriteError, match="failed to write tmp"):
                write_record(dest, valid_record, validator)

    def test_read_bytes_oserror_cleans_tmp(
        self, tmp_path: Path, validator: SchemaValidator, valid_record: dict[str, Any]
    ) -> None:
        dest = tmp_path / "r-001.json"
        _calls: list[int] = [0]
        _original_read = Path.read_bytes

        def _fail_second_read(self_path: Path) -> bytes:
            _calls[0] += 1
            if _calls[0] == 1:
                raise OSError("read failed")
            return _original_read(self_path)

        with patch.object(Path, "read_bytes", _fail_second_read):
            with pytest.raises(AtomicWriteError, match="failed to read back"):
                write_record(dest, valid_record, validator)

        tmp_file = dest.parent / (dest.name + ".tmp")
        assert not tmp_file.exists()

    def test_read_bytes_invalid_json_cleans_tmp(
        self, tmp_path: Path, validator: SchemaValidator, valid_record: dict[str, Any]
    ) -> None:
        dest = tmp_path / "r-001.json"
        _calls: list[int] = [0]
        _original_read = Path.read_bytes

        def _return_bad_json(self_path: Path) -> bytes:
            _calls[0] += 1
            if _calls[0] == 1:
                return b"NOT VALID JSON {"
            return _original_read(self_path)

        with patch.object(Path, "read_bytes", _return_bad_json):
            with pytest.raises(AtomicWriteError, match="failed to read back"):
                write_record(dest, valid_record, validator)

        tmp_file = dest.parent / (dest.name + ".tmp")
        assert not tmp_file.exists()

    def test_unlink_failure_logs_warning(
        self, tmp_path: Path, validator: SchemaValidator, valid_record: dict[str, Any], caplog: Any
    ) -> None:
        import logging
        dest = tmp_path / "r-001.json"
        _original_unlink = Path.unlink

        def _fail_unlink(self_path: Path, **kwargs: Any) -> None:
            if str(self_path).endswith(".tmp"):
                raise OSError("cannot delete")
            _original_unlink(self_path, **kwargs)

        with patch("helm_controller.scr.atomic_write.os.replace", side_effect=OSError("crash")):
            with patch.object(Path, "unlink", _fail_unlink):
                with caplog.at_level(logging.WARNING, logger="helm_controller.scr.atomic_write"):
                    with pytest.raises(OSError):
                        write_record(dest, valid_record, validator)
        assert any("could not remove tmp file" in r.message for r in caplog.records)
