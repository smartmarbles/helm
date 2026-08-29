"""Branch-coverage tests for the stdlib JSON Schema engine.

The four real contract schemas always pair a ``type`` constraint with the other
keywords, so they never exercise the engine's defensive type guards or the
``additionalProperties: true`` / ``if``/``else`` arcs. These synthetic-schema
tests drive the engine directly to lock those branches at 100%.
"""

from __future__ import annotations

import pytest

from helm_controller.contracts._jsonschema_lite import compile_schema


def _errors(schema: dict, instance) -> list[str]:
    return [message for _, message in compile_schema(schema).collect(instance)]


# --- type predicates: accept + reject for every supported type ------------


@pytest.mark.parametrize(
    ("type_name", "ok", "bad"),
    [
        ("null", None, 0),
        ("boolean", True, 1),
        ("integer", 5, True),
        ("integer", 5, "x"),
        ("string", "x", 5),
        ("array", [], {}),
        ("object", {}, []),
    ],
)
def test_type_predicate_branches(type_name, ok, bad) -> None:
    schema = {"type": type_name}
    assert _errors(schema, ok) == []
    assert _errors(schema, bad)


def test_type_union_membership() -> None:
    schema = {"type": ["string", "null"]}
    assert _errors(schema, "x") == []
    assert _errors(schema, None) == []
    assert _errors(schema, 5)


# --- container-keyword guards on wrong instance types ---------------------


def test_min_length_ignored_on_non_string() -> None:
    assert _errors({"minLength": 3}, 5) == []


def test_minimum_ignored_on_bool_and_non_number() -> None:
    assert _errors({"minimum": 0}, True) == []
    assert _errors({"minimum": 0}, "x") == []
    assert _errors({"minimum": 0}, -1)


def test_required_ignored_on_non_object() -> None:
    assert _errors({"required": ["a"]}, "not-an-object") == []


def test_properties_ignored_on_non_object() -> None:
    assert _errors({"properties": {"a": {"type": "string"}}}, 5) == []


def test_property_names_ignored_on_non_object() -> None:
    assert _errors({"propertyNames": {"pattern": "^x$"}}, 5) == []


def test_items_ignored_on_non_array() -> None:
    assert _errors({"items": {"type": "string"}}, 5) == []


# --- additionalProperties boolean arcs ------------------------------------


def test_additional_properties_true_allows_extra() -> None:
    schema = {"additionalProperties": True, "properties": {}}
    assert _errors(schema, {"extra": 1}) == []


def test_additional_properties_false_ignored_on_non_object() -> None:
    assert _errors({"additionalProperties": False}, 5) == []


# --- if / then / else -----------------------------------------------------


def test_if_else_branch_applies_when_if_fails() -> None:
    schema = {
        "if": {"const": "x"},
        "then": {"type": "integer"},
        "else": {"type": "string"},
    }
    # "y" != "x" => if fails => else (must be string) applies => "y" ok.
    assert _errors(schema, "y") == []
    # 5 != "x" => else (string) applies => 5 violates.
    assert _errors(schema, 5)


def test_if_then_branch_applies_when_if_matches() -> None:
    schema = {"if": {"const": "x"}, "then": {"minLength": 5}}
    assert _errors(schema, "x")  # "x" matches if, then requires len>=5
