"""Tests for the concurrency / owner-lease error classes (spec015 Task 2.4).

Each error is constructed via its full constructor signature; attributes and the
formatted message are asserted directly because ``test_locking.py`` reaches these
classes only through raising paths and cannot assert every stored attribute.
"""

from __future__ import annotations

from helm_controller.store.adapter import StoreError
from helm_controller.store.errors import (
    LockConflictError,
    LockExpiredError,
    LockNotHeldError,
    StaleRevisionError,
)
from helm_controller.store.identity import RuntimeIdentity

_IDENT = RuntimeIdentity("sess-1", "wf-1", "turn-1")


def test_stale_revision_error() -> None:
    err = StaleRevisionError(_IDENT, expected_revision=3, actual_revision=5)
    assert isinstance(err, StoreError)
    assert err.identity is _IDENT
    assert err.expected_revision == 3
    assert err.actual_revision == 5
    assert "expected 3, store holds 5" in str(err)


def test_lock_not_held_error() -> None:
    err = LockNotHeldError(_IDENT, "owner lease has expired")
    assert isinstance(err, StoreError)
    assert err.identity is _IDENT
    assert err.reason == "owner lease has expired"
    assert "no valid owner lease" in str(err)
    assert "owner lease has expired" in str(err)


def test_lock_conflict_error() -> None:
    err = LockConflictError(_IDENT, current_owner="AGENT_B")
    assert isinstance(err, StoreError)
    assert err.identity is _IDENT
    assert err.current_owner == "AGENT_B"
    assert "'AGENT_B'" in str(err)


def test_lock_expired_error() -> None:
    err = LockExpiredError(_IDENT, lock_token="tok-1", expires_at="2026-01-01T00:00:00Z")
    assert isinstance(err, StoreError)
    assert err.identity is _IDENT
    assert err.lock_token == "tok-1"
    assert err.expires_at == "2026-01-01T00:00:00Z"
    assert "'tok-1'" in str(err)
    assert "2026-01-01T00:00:00Z" in str(err)
    assert "mid-operation" in str(err)
