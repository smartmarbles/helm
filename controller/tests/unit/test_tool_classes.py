"""Tests for helm_controller.policy.tool_classes (spec015 Task 4.4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from helm_controller.policy.tool_classes import (
    POLICY_CLASSES,
    UNKNOWN_CLASS,
    ToolClassError,
    ToolClassMap,
    ToolEntry,
    _load_class_map,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def minimal_data_file(tmp_path: Path) -> Path:
    p = tmp_path / "tool_classes.json"
    p.write_text(
        json.dumps(
            {
                "version": "1.0",
                "classes": {
                    "read": ["read_file", "grep_search"],
                    "file_mutation": [
                        {"name": "create_file", "path_fields": ["filePath"]},
                        {
                            "name": "multi_replace",
                            "path_fields": ["replacements[*].filePath"],
                        },
                    ],
                    "execution": ["run_in_terminal"],
                },
            }
        ),
        encoding="utf-8",
    )
    return p


# ---------------------------------------------------------------------------
# _load_class_map — happy path
# ---------------------------------------------------------------------------


def test_load_string_entries(minimal_data_file: Path) -> None:
    mapping = _load_class_map(minimal_data_file)
    assert mapping["read_file"].policy_class == "read"
    assert mapping["grep_search"].policy_class == "read"
    assert mapping["run_in_terminal"].policy_class == "execution"


def test_load_dict_entry_with_path_fields(minimal_data_file: Path) -> None:
    mapping = _load_class_map(minimal_data_file)
    entry = mapping["create_file"]
    assert entry.policy_class == "file_mutation"
    assert entry.path_fields == ("filePath",)


def test_load_dict_entry_array_path_fields(minimal_data_file: Path) -> None:
    mapping = _load_class_map(minimal_data_file)
    entry = mapping["multi_replace"]
    assert entry.path_fields == ("replacements[*].filePath",)


# ---------------------------------------------------------------------------
# _load_class_map — error branches
# ---------------------------------------------------------------------------


def test_load_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ToolClassError, match="Cannot read"):
        _load_class_map(tmp_path / "nope.json")


def test_load_malformed_json(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("{bad", encoding="utf-8")
    with pytest.raises(ToolClassError, match="Malformed JSON"):
        _load_class_map(p)


def test_load_missing_classes_key(tmp_path: Path) -> None:
    p = tmp_path / "no_classes.json"
    p.write_text(json.dumps({"version": "1.0"}), encoding="utf-8")
    with pytest.raises(ToolClassError, match="missing top-level 'classes' dict"):
        _load_class_map(p)


def test_load_classes_not_dict(tmp_path: Path) -> None:
    p = tmp_path / "classes_list.json"
    p.write_text(json.dumps({"classes": ["read"]}), encoding="utf-8")
    with pytest.raises(ToolClassError, match="missing top-level 'classes' dict"):
        _load_class_map(p)


def test_load_class_entries_not_list(tmp_path: Path) -> None:
    p = tmp_path / "entries_not_list.json"
    p.write_text(json.dumps({"classes": {"read": "not_a_list"}}), encoding="utf-8")
    with pytest.raises(ToolClassError, match="must be a list"):
        _load_class_map(p)


def test_load_dict_entry_missing_name(tmp_path: Path) -> None:
    p = tmp_path / "no_name.json"
    p.write_text(
        json.dumps({"classes": {"file_mutation": [{"path_fields": ["filePath"]}]}}),
        encoding="utf-8",
    )
    with pytest.raises(ToolClassError, match="missing 'name'"):
        _load_class_map(p)


def test_load_invalid_entry_type(tmp_path: Path) -> None:
    p = tmp_path / "bad_entry.json"
    p.write_text(json.dumps({"classes": {"read": [123]}}), encoding="utf-8")
    with pytest.raises(ToolClassError, match="Invalid entry type"):
        _load_class_map(p)


# ---------------------------------------------------------------------------
# ToolClassMap — classify
# ---------------------------------------------------------------------------


def test_classify_known_tool_returns_entry(minimal_data_file: Path) -> None:
    tcm = ToolClassMap(minimal_data_file)
    entry = tcm.classify("read_file")
    assert isinstance(entry, ToolEntry)
    assert entry.policy_class == "read"
    assert entry.name == "read_file"


def test_classify_unknown_tool_returns_unknown_class(minimal_data_file: Path) -> None:
    tcm = ToolClassMap(minimal_data_file)
    entry = tcm.classify("nonexistent_tool")
    assert entry.policy_class == UNKNOWN_CLASS
    assert entry.name == "nonexistent_tool"


# ---------------------------------------------------------------------------
# ToolClassMap — known_tools
# ---------------------------------------------------------------------------


def test_known_tools_contains_all_loaded(minimal_data_file: Path) -> None:
    tcm = ToolClassMap(minimal_data_file)
    known = tcm.known_tools()
    assert "read_file" in known
    assert "create_file" in known
    assert "nonexistent_tool" not in known


# ---------------------------------------------------------------------------
# POLICY_CLASSES constant
# ---------------------------------------------------------------------------


def test_policy_classes_contains_seven_classes() -> None:
    assert POLICY_CLASSES == {
        "read",
        "workflow_state",
        "agent_dispatch",
        "file_mutation",
        "web_external",
        "vscode_system",
        "execution",
    }


# ---------------------------------------------------------------------------
# Default bundled data file
# ---------------------------------------------------------------------------


def test_default_data_file_classifies_known_tools() -> None:
    tcm = ToolClassMap()
    assert tcm.classify("read_file").policy_class == "read"
    assert tcm.classify("run_in_terminal").policy_class == "execution"
    assert tcm.classify("create_file").policy_class == "file_mutation"
    assert tcm.classify("run_task").policy_class == "vscode_system"
    assert tcm.classify("session_store_sql").policy_class == "workflow_state"
    assert tcm.classify("runSubagent").policy_class == "agent_dispatch"


def test_default_data_file_unknown_tool() -> None:
    tcm = ToolClassMap()
    assert tcm.classify("totally_unknown_tool_xyz").policy_class == UNKNOWN_CLASS


def test_default_data_file_file_mutation_path_fields() -> None:
    tcm = ToolClassMap()
    create_entry = tcm.classify("create_file")
    assert "filePath" in create_entry.path_fields

    multi_entry = tcm.classify("multi_replace_string_in_file")
    assert "replacements[*].filePath" in multi_entry.path_fields


def test_default_data_file_create_new_jupyter_no_path_fields() -> None:
    tcm = ToolClassMap()
    entry = tcm.classify("create_new_jupyter_notebook")
    assert entry.policy_class == "file_mutation"
    assert entry.path_fields == ()
