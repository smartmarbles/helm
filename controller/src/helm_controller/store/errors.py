"""Concurrency and owner-lease error classes (spec015 Task 2.4).

These errors layer on top of the adapter's :class:`StoreError` base so callers
may catch the whole runtime-store family with a single ``except StoreError``
while still discriminating the precise concurrency failure mode.

The split between :class:`StaleRevisionError` / :class:`LockNotHeldError` and
:class:`LockExpiredError` is load-bearing (plan Watch Out #6, spec §5.3):

* **Rule 5 — pre-write reject.** A mutation *request* arrives carrying a stale
  ``expected_revision`` (:class:`StaleRevisionError`) or finds no valid owner
  lease at the moment it tries to start (:class:`LockNotHeldError`). The request
  is refused *before any mutation begins*. Maps to a ``deny`` decision.
* **Rule 6 — mid-operation expiry.** A lease the caller already holds expires
  *between acquire and complete* (:class:`LockExpiredError`). This is NOT a
  rejected request; it is a correction-path signal — the controller must
  reacquire within policy or terminalize the workflow.

These two are distinct failure modes and MUST NOT be conflated: Rule 5 blocks
the start of a new mutation; Rule 6 governs an in-flight operation that lost its
lease.
"""

from __future__ import annotations

from helm_controller.store.adapter import StoreError
from helm_controller.store.identity import RuntimeIdentity


class StaleRevisionError(StoreError):
    """Rule 5 pre-write reject: ``expected_revision`` no longer matches the store.

    Raised before any mutation is applied when an incoming compare-and-swap
    carries a revision that has already been superseded.
    """

    def __init__(
        self,
        identity: RuntimeIdentity,
        expected_revision: int,
        actual_revision: int,
    ) -> None:
        self.identity = identity
        self.expected_revision = expected_revision
        self.actual_revision = actual_revision
        super().__init__(
            f"stale revision for {identity!r}: "
            f"expected {expected_revision}, store holds {actual_revision}"
        )


class LockNotHeldError(StoreError):
    """Rule 5 pre-write reject: no valid owner lease at mutation-start time.

    Raised before any mutation is applied when the workflow holds no active
    owner lease, the lease is held by a different owner, or the lease has
    already expired at the moment the request tries to begin.
    """

    def __init__(self, identity: RuntimeIdentity, reason: str) -> None:
        self.identity = identity
        self.reason = reason
        super().__init__(f"no valid owner lease for {identity!r}: {reason}")


class LockConflictError(StoreError):
    """Acquire rejected: a different owner holds a live, unexpired lease."""

    def __init__(self, identity: RuntimeIdentity, current_owner: str) -> None:
        self.identity = identity
        self.current_owner = current_owner
        super().__init__(
            f"owner lease for {identity!r} is held by {current_owner!r}"
        )


class LockExpiredError(StoreError):
    """Rule 6 correction signal: a held lease expired mid-operation.

    Distinct from :class:`LockNotHeldError`: this is raised for a lease the
    caller *already acquired* and was operating under, not for a fresh request
    being rejected at the gate. The caller must enter the correction path —
    reacquire within policy limits or terminalize the workflow.
    """

    def __init__(
        self,
        identity: RuntimeIdentity,
        lock_token: str,
        expires_at: str,
    ) -> None:
        self.identity = identity
        self.lock_token = lock_token
        self.expires_at = expires_at
        super().__init__(
            f"owner lease {lock_token!r} for {identity!r} "
            f"expired at {expires_at} mid-operation"
        )
