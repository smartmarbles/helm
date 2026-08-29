"""Minimal stdlib-only JSON Schema validator for the four Helm contracts.

This module replaces the third-party ``jsonschema`` runtime dependency with a
hand-written validator covering exactly the bounded keyword surface the four
contract schemas (``runtime-snapshot``, ``blackboard-row``, ``hook-envelope``,
``decision-output``) actually use. It deliberately reproduces today's
observable behavior, including:

* aggregate-all-errors (non-fail-fast) collection, sorted by JSON path; and
* ``format`` (and every annotation keyword) treated as a NO-OP — ``date-time``
  is accepted regardless of shape, matching the prior ``jsonschema`` setup
  which wired no ``format_checker``.

Supported keywords: ``type`` (single + union arrays), ``enum``, ``const``,
``pattern``, ``minLength``, ``minimum``, ``required``, ``properties``,
``additionalProperties`` (boolean), ``propertyNames``, ``items``, ``$ref``
(local ``#/$defs/...`` JSON pointer), ``oneOf``, ``allOf``, ``if``/``then``/
``else``, and ``not``. ``$defs`` and all annotation keywords (``$schema``,
``$id``, ``version``, ``title``, ``description``, ``$comment``,
``x-storage-tier``, ``format``) are ignored during validation.

The authored schemas are trusted repo artifacts; unlike ``jsonschema`` this
engine performs no meta-schema (``check_schema``) validation of the authored
schema itself.
"""

from __future__ import annotations

import re
from typing import Any

Error = tuple[tuple[Any, ...], str]

_TYPE_PREDICATES = {
    "null": lambda value: value is None,
    "boolean": lambda value: isinstance(value, bool),
    "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
    "string": lambda value: isinstance(value, str),
    "array": lambda value: isinstance(value, list),
    "object": lambda value: isinstance(value, dict),
}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class SchemaValidator:
    """Compiled validator for a single contract schema."""

    __slots__ = ("_root",)

    def __init__(self, root: dict[str, Any]) -> None:
        self._root = root

    def collect(self, instance: Any) -> list[Error]:
        """Return every (path, message) violation of ``instance``."""
        errors: list[Error] = []
        self._visit(instance, self._root, (), errors)
        return errors

    def _visit(
        self,
        instance: Any,
        schema: dict[str, Any],
        path: tuple[Any, ...],
        errors: list[Error],
    ) -> None:
        for keyword, value in schema.items():
            handler = _HANDLERS.get(keyword)
            if handler is not None:
                handler(self, instance, value, schema, path, errors)

    def _validates(self, instance: Any, schema: dict[str, Any]) -> bool:
        scratch: list[Error] = []
        self._visit(instance, schema, (), scratch)
        return not scratch

    def _resolve(self, ref: str) -> dict[str, Any]:
        node: Any = self._root
        for part in ref[2:].split("/"):
            node = node[part]
        return node

    # --- keyword handlers -------------------------------------------------

    def _h_type(self, instance, value, schema, path, errors) -> None:
        names = value if isinstance(value, list) else [value]
        if not any(_TYPE_PREDICATES[name](instance) for name in names):
            errors.append((path, f"{instance!r} is not of type {', '.join(names)}"))

    def _h_enum(self, instance, value, schema, path, errors) -> None:
        if instance not in value:
            errors.append((path, f"{instance!r} is not one of {value!r}"))

    def _h_const(self, instance, value, schema, path, errors) -> None:
        if instance != value:
            errors.append((path, f"{instance!r} was expected to be {value!r}"))

    def _h_pattern(self, instance, value, schema, path, errors) -> None:
        if isinstance(instance, str) and re.search(value, instance) is None:
            errors.append((path, f"{instance!r} does not match {value!r}"))

    def _h_min_length(self, instance, value, schema, path, errors) -> None:
        if isinstance(instance, str) and len(instance) < value:
            errors.append((path, f"{instance!r} is shorter than {value}"))

    def _h_minimum(self, instance, value, schema, path, errors) -> None:
        if _is_number(instance) and instance < value:
            errors.append((path, f"{instance!r} is less than the minimum of {value}"))

    def _h_required(self, instance, value, schema, path, errors) -> None:
        if isinstance(instance, dict):
            for name in value:
                if name not in instance:
                    errors.append((path, f"{name!r} is a required property"))

    def _h_properties(self, instance, value, schema, path, errors) -> None:
        if isinstance(instance, dict):
            for key, subschema in value.items():
                if key in instance:
                    self._visit(instance[key], subschema, path + (key,), errors)

    def _h_additional_properties(self, instance, value, schema, path, errors) -> None:
        if value or not isinstance(instance, dict):
            return
        allowed = schema.get("properties", {})
        for key in instance:
            if key not in allowed:
                errors.append(
                    (path + (key,), f"additional property {key!r} is not allowed")
                )

    def _h_property_names(self, instance, value, schema, path, errors) -> None:
        if isinstance(instance, dict):
            for key in instance:
                self._visit(key, value, path + (key,), errors)

    def _h_items(self, instance, value, schema, path, errors) -> None:
        if isinstance(instance, list):
            for index, element in enumerate(instance):
                self._visit(element, value, path + (index,), errors)

    def _h_ref(self, instance, value, schema, path, errors) -> None:
        self._visit(instance, self._resolve(value), path, errors)

    def _h_one_of(self, instance, value, schema, path, errors) -> None:
        matches = sum(1 for sub in value if self._validates(instance, sub))
        if matches != 1:
            errors.append(
                (path, f"{instance!r} is not valid under exactly one subschema")
            )

    def _h_all_of(self, instance, value, schema, path, errors) -> None:
        for sub in value:
            self._visit(instance, sub, path, errors)

    def _h_if(self, instance, value, schema, path, errors) -> None:
        if self._validates(instance, value):
            branch = schema.get("then")
        else:
            branch = schema.get("else")
        if branch is not None:
            self._visit(instance, branch, path, errors)

    def _h_not(self, instance, value, schema, path, errors) -> None:
        if self._validates(instance, value):
            errors.append((path, f"{instance!r} is valid under the 'not' subschema"))


_HANDLERS = {
    "type": SchemaValidator._h_type,
    "enum": SchemaValidator._h_enum,
    "const": SchemaValidator._h_const,
    "pattern": SchemaValidator._h_pattern,
    "minLength": SchemaValidator._h_min_length,
    "minimum": SchemaValidator._h_minimum,
    "required": SchemaValidator._h_required,
    "properties": SchemaValidator._h_properties,
    "additionalProperties": SchemaValidator._h_additional_properties,
    "propertyNames": SchemaValidator._h_property_names,
    "items": SchemaValidator._h_items,
    "$ref": SchemaValidator._h_ref,
    "oneOf": SchemaValidator._h_one_of,
    "allOf": SchemaValidator._h_all_of,
    "if": SchemaValidator._h_if,
    "not": SchemaValidator._h_not,
}


def compile_schema(schema: dict[str, Any]) -> SchemaValidator:
    """Compile a contract schema into a reusable :class:`SchemaValidator`."""
    return SchemaValidator(schema)
