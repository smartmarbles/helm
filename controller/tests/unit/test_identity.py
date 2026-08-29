"""Tests for the composite runtime identity model (spec015 Task 2.2/2.4).

``test_store_adapter.py`` only exercises the valid-identity path; the
validation-failure branches of :class:`RuntimeIdentity.__post_init__` and the
single-source ``workflow_id`` generation guarantee require direct invocation to
reach 100% branch coverage.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

import pytest

import helm_controller
from helm_controller.scr.identity import new_record_id
from helm_controller.store.identity import (
    IdentityError,
    RuntimeIdentity,
    new_workflow_id,
)
from helm_controller.store.locking import new_lock_token

# Registry of sanctioned UUID-minting factories: (relative posix path under the
# package root, factory function name). Every ``str(uuid.uuid4())`` source line
# in the package MUST originate from exactly one of these factories; any other
# uuid4 mint is required to be a lock token (substring ``"token"``). Matching is
# keyed on RELATIVE PATH — never bare filename — because both the runtime-store
# and SCR tiers define their own ``identity.py``.
_SANCTIONED_FACTORIES: tuple[tuple[str, str], ...] = (
    ("store/identity.py", "new_workflow_id"),
    ("scr/identity.py", "new_record_id"),
    ("store/locking.py", "new_lock_token"),
)


def test_valid_composite_identity_construction() -> None:
    ident = RuntimeIdentity("sess-1", "wf-1", "turn-1")
    assert ident.session_id == "sess-1"
    assert ident.workflow_id == "wf-1"
    assert ident.turn_id == "turn-1"


def test_session_id_none_branch() -> None:
    with pytest.raises(IdentityError, match="session_id must not be None"):
        RuntimeIdentity(None, "wf-1", "turn-1")  # type: ignore[arg-type]


def test_workflow_id_none_branch() -> None:
    with pytest.raises(IdentityError, match="workflow_id must not be None"):
        RuntimeIdentity("sess-1", None, "turn-1")  # type: ignore[arg-type]


def test_turn_id_null_branch() -> None:
    with pytest.raises(IdentityError, match="turn_id must not be None"):
        RuntimeIdentity("sess-1", "wf-1", None)  # type: ignore[arg-type]


def test_non_str_field_branch() -> None:
    with pytest.raises(IdentityError, match="workflow_id must be a str, got int"):
        RuntimeIdentity("sess-1", 123, "turn-1")  # type: ignore[arg-type]


def test_empty_field_branch() -> None:
    with pytest.raises(IdentityError, match="turn_id must not be empty"):
        RuntimeIdentity("sess-1", "wf-1", "")


def test_equality_and_hashing() -> None:
    a = RuntimeIdentity("sess-1", "wf-1", "turn-1")
    b = RuntimeIdentity("sess-1", "wf-1", "turn-1")
    c = RuntimeIdentity("sess-1", "wf-1", "turn-2")
    assert a == b
    assert a != c
    assert hash(a) == hash(b)
    # Usable as a dict key (frozen + hashable).
    index = {a: "first"}
    index[b] = "second"
    assert index[a] == "second"
    assert len(index) == 1
    assert c not in index


def test_new_workflow_id_returns_unique_uuid_strings() -> None:
    first = new_workflow_id()
    second = new_workflow_id()
    assert first != second
    # Each value is a parseable canonical UUID string.
    assert str(uuid.UUID(first)) == first
    assert str(uuid.UUID(second)) == second


def test_new_record_id_returns_unique_uuid_strings() -> None:
    first = new_record_id()
    second = new_record_id()
    assert first != second
    # Each value is a parseable canonical UUID string.
    assert str(uuid.UUID(first)) == first
    assert str(uuid.UUID(second)) == second


def test_new_lock_token_returns_unique_uuid_strings() -> None:
    first = new_lock_token()
    second = new_lock_token()
    assert first != second
    # Each value is a parseable canonical UUID string.
    assert str(uuid.UUID(first)) == first
    assert str(uuid.UUID(second)) == second


def test_uuid_minting_is_single_source_per_sanctioned_factory() -> None:
    """Grep guard: every ``str(uuid.uuid4())`` mint is sanctioned or a token.

    Enforces the plan's single-source mandate (Task 2.4) generalized across all
    identifier tiers. Each sanctioned factory in ``_SANCTIONED_FACTORIES`` must
    be defined exactly once and contribute exactly one ``str(uuid.uuid4())``
    source line; every other code-level uuid mint must be a lock token. Matching
    is keyed on RELATIVE PATH, not bare filename, because the runtime-store and
    SCR tiers each define their own ``identity.py``.
    """
    src_root = Path(helm_controller.__file__).resolve().parent
    gen_pattern = re.compile(r"(?:return|=)\s*str\(uuid\.uuid4\(\)\)")
    sanctioned_by_path = {rel: name for rel, name in _SANCTIONED_FACTORIES}

    def_counts: dict[str, int] = {name: 0 for _rel, name in _SANCTIONED_FACTORIES}
    source_line_counts: dict[str, int] = {rel: 0 for rel, _name in _SANCTIONED_FACTORIES}
    other_uuid_uses: list[tuple[str, str]] = []

    for py_file in src_root.rglob("*.py"):
        rel = py_file.relative_to(src_root).as_posix()
        text = py_file.read_text(encoding="utf-8")
        if rel in sanctioned_by_path:
            factory_name = sanctioned_by_path[rel]
            def_pattern = re.compile(
                rf"^def\s+{re.escape(factory_name)}\b", re.MULTILINE
            )
            def_counts[factory_name] += len(def_pattern.findall(text))
        for line in text.splitlines():
            if not gen_pattern.search(line):
                continue
            if rel in sanctioned_by_path:
                source_line_counts[rel] += 1
            else:
                other_uuid_uses.append((rel, line.strip()))

    # Each sanctioned factory is defined exactly once and mints exactly one line.
    for rel, name in _SANCTIONED_FACTORIES:
        assert def_counts[name] == 1, f"{name} must be defined exactly once"
        assert source_line_counts[rel] == 1, (
            f"{rel} must contain exactly one uuid4 source line"
        )

    # Every other code-level uuid mint is a lock token, never an ad-hoc id.
    for _rel, line in other_uuid_uses:
        assert "token" in line
        assert "workflow_id" not in line
        assert "record_id" not in line
