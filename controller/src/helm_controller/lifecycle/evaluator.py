"""Lifecycle boundary evaluator entry point — Task 7.2 (spec §3.3, §4.4, §4.5).

The authoritative, un-bypassable entry point for every workflow lifecycle
boundary event. :meth:`LifecycleBoundaryEvaluator.evaluate` resolves the source
lifecycle, consults the §4.4 legality matrix (:mod:`.legality`), and then either
DENIES (illegal — fail closed, no store write) or APPLIES the legal mutation
through the runtime-store write path.

ST-000 disambiguation (spec §4.5 final block): ST-000 (IDLE) covers initial IDLE
(no non-terminal workflow in session) and suspended IDLE (a non-terminal
suspended workflow exists). For a ``new`` event the source lifecycle is resolved
from :class:`SessionWorkflowState`: a present suspended workflow resolves to
``NON_TERMINAL_SUSPENDED`` → ``new`` is ILLEGAL, so TR-004 (auto-start) cannot
fire over a suspended workflow and the suspended workflow is never discarded.

Write-path design note (deliberate, ADR-relevant): boundary lifecycle
transitions are applied via the adapter write path directly rather than the
lease-scoped :meth:`LockManager.compare_and_swap` for the lifecycle-flipping
steps. The §5.3 lease model couples a held lease to an *active* lifecycle (the
``workflow_lifecycle = 'non_terminal_active' OR owner_lock_active IS NULL`` schema
CHECK), so suspend/terminalize — which drop the lock while flipping to
suspended/terminal — cannot be expressed as a lease-held CAS. The substantive
§5.3 guarantees are preserved on every boundary write: the optimistic-concurrency
``revision`` is advanced (read-then ``revision = expected + 1``), a
``mutation_audit`` row with a durable ``operation_id`` idempotency key is written
atomically (double-commit guard), and terminal immutability is enforced by the
adapter (a terminal row rejects all further mutation). Granting a lock (``new``,
``resume``, supersede successor) still goes through :class:`LockManager` so lock
token/lease logic is never re-implemented here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from helm_controller.lifecycle.legality import (
    LIFECYCLE_ACTIVE,
    LIFECYCLE_SUSPENDED,
    LIFECYCLE_TERMINAL,
    BoundaryEvent,
    LegalityResult,
    SourceLifecycle,
    StateMutation,
    evaluate_legality,
)
from helm_controller.lifecycle.prior_state import prior_state_mutation
from helm_controller.lifecycle.terminalize import (
    TERMINAL_REASON_BY_STATE,
    is_terminal_transition,
    terminal_state_for,
)
from helm_controller.store.adapter import (
    MutationAudit,
    RuntimeStoreAdapter,
    RuntimeStoreRecord,
)
from helm_controller.store.identity import RuntimeIdentity, new_workflow_id
from helm_controller.store.locking import LockManager, idempotency_key

_ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BoundaryRequestError(ValueError):
    """Raised when a boundary request is internally inconsistent (programming error)."""


@dataclass(frozen=True)
class SessionWorkflowState:
    """Session-registry view used to disambiguate ST-000 for a ``new`` event (§4.5).

    Routing/audit metadata only (spec §3.3) — never a second legality engine.
    """

    active_workflow_id: str | None = None
    suspended_workflow_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class NewWorkflowSeed:
    """Caller-supplied content for a ``new`` / ``supersede`` successor workflow.

    The evaluator owns the *identity and lifecycle* decisions (it allocates the
    ``workflow_id`` and sets lifecycle/linkage/lock); the caller supplies the
    workflow row content.
    """

    row_id: str
    item_id: str
    immutable_fields_hash: str
    initial_fsm_state: str = "ST-000"
    created_by: str = "SYSTEM"


@dataclass(frozen=True)
class BoundaryRequest:
    """A candidate boundary event submitted to the evaluator."""

    event: BoundaryEvent
    session_id: str
    turn_id: str
    owner_agent: str
    target_workflow_id: str | None = None
    session_state: SessionWorkflowState = field(default_factory=SessionWorkflowState)
    new_seed: NewWorkflowSeed | None = None
    transition_id: str | None = None
    terminal_state: str | None = None


@dataclass(frozen=True)
class BoundaryDecision:
    """The evaluator's verdict for one boundary event."""

    applied: bool
    legal: bool
    event: BoundaryEvent
    source: SourceLifecycle
    reason: str
    mutation: StateMutation | None
    workflow_id: str | None
    predecessor_workflow_id: str | None
    successor_workflow_id: str | None
    boundary_event: str | None
    prior_non_terminal_fsm_state: str | None
    record: RuntimeStoreRecord | None


class LifecycleBoundaryEvaluator:
    """Authoritative entry point for ``new``/``supersede``/``suspend``/``resume``/``terminalize``."""

    def __init__(
        self,
        adapter: RuntimeStoreAdapter,
        lock_manager: LockManager,
        *,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._adapter = adapter
        self._locks = lock_manager
        self._clock = clock

    def evaluate(self, request: BoundaryRequest) -> BoundaryDecision:
        """Resolve source lifecycle, check §4.4 legality, then apply or deny."""
        source, record = self._resolve_source(request)
        legality = evaluate_legality(request.event, source)
        if not legality.legal:
            return self._denied(request, source, legality)
        return self._apply(request, source, legality, record)

    # ----------------------------------------------------------------- #
    # Source-lifecycle resolution (incl. ST-000 disambiguation).
    # ----------------------------------------------------------------- #
    def _resolve_source(
        self, request: BoundaryRequest
    ) -> tuple[SourceLifecycle, RuntimeStoreRecord | None]:
        if request.event is BoundaryEvent.NEW:
            session_state = request.session_state
            if session_state.active_workflow_id is not None:
                return SourceLifecycle.NON_TERMINAL_ACTIVE, None
            if session_state.suspended_workflow_ids:
                # Suspended IDLE: TR-004 MUST NOT auto-fire (§4.5).
                return SourceLifecycle.NON_TERMINAL_SUSPENDED, None
            return SourceLifecycle.NONE, None
        if request.target_workflow_id is None:
            return SourceLifecycle.NONE, None
        identity = RuntimeIdentity(
            request.session_id, request.target_workflow_id, request.turn_id
        )
        record = self._adapter.read(identity)
        if record is None:
            return SourceLifecycle.NONE, None
        return self._lifecycle_of(record), record

    @staticmethod
    def _lifecycle_of(record: RuntimeStoreRecord) -> SourceLifecycle:
        lifecycle = record.row.workflow_lifecycle
        if lifecycle == LIFECYCLE_ACTIVE:
            return SourceLifecycle.NON_TERMINAL_ACTIVE
        if lifecycle == LIFECYCLE_SUSPENDED:
            return SourceLifecycle.NON_TERMINAL_SUSPENDED
        return SourceLifecycle.TERMINAL

    # ----------------------------------------------------------------- #
    # Apply dispatch.
    # ----------------------------------------------------------------- #
    def _apply(
        self,
        request: BoundaryRequest,
        source: SourceLifecycle,
        legality: LegalityResult,
        record: RuntimeStoreRecord | None,
    ) -> BoundaryDecision:
        event = request.event
        if event is BoundaryEvent.NEW:
            return self._apply_new(request, source, legality)
        if event is BoundaryEvent.SUPERSEDE:
            return self._apply_supersede(request, source, legality)
        if event is BoundaryEvent.SUSPEND:
            return self._apply_suspend(request, source, legality, record)
        if event is BoundaryEvent.RESUME:
            return self._apply_resume(request, source, legality, record)
        return self._apply_terminalize(request, source, legality, record)

    def _apply_new(
        self,
        request: BoundaryRequest,
        source: SourceLifecycle,
        legality: LegalityResult,
    ) -> BoundaryDecision:
        seed = self._require_seed(request)
        new_id = new_workflow_id()
        identity = RuntimeIdentity(request.session_id, new_id, request.turn_id)
        self._create(identity, seed)
        lease = self._locks.acquire(identity, request.owner_agent)
        revision = self._revision(identity)
        record = self._locks.compare_and_swap(
            lease,
            revision,
            operation="boundary_new",
            operation_id=idempotency_key(
                request.session_id, new_id, request.turn_id, "boundary_new"
            ),
            workflow_fields={"boundary_event": BoundaryEvent.NEW.value},
        )
        return self._decision(
            applied=True,
            request=request,
            source=source,
            legality=legality,
            workflow_id=new_id,
            boundary_event=BoundaryEvent.NEW.value,
            record=record,
        )

    def _apply_supersede(
        self,
        request: BoundaryRequest,
        source: SourceLifecycle,
        legality: LegalityResult,
    ) -> BoundaryDecision:
        seed = self._require_seed(request)
        predecessor_id = request.target_workflow_id
        assert predecessor_id is not None  # legal supersede requires a target
        new_id = new_workflow_id()
        succ_identity = RuntimeIdentity(request.session_id, new_id, request.turn_id)
        self._create(succ_identity, seed)
        lease = self._locks.acquire(succ_identity, request.owner_agent)
        revision = self._revision(succ_identity)
        succ_record = self._locks.compare_and_swap(
            lease,
            revision,
            operation="boundary_supersede",
            operation_id=idempotency_key(
                request.session_id, new_id, request.turn_id, "boundary_supersede"
            ),
            workflow_fields={
                "predecessor_workflow_id": predecessor_id,
                "boundary_event": BoundaryEvent.SUPERSEDE.value,
            },
        )
        self._terminalize_predecessor(request, predecessor_id, new_id)
        return self._decision(
            applied=True,
            request=request,
            source=source,
            legality=legality,
            workflow_id=new_id,
            predecessor_workflow_id=predecessor_id,
            boundary_event=BoundaryEvent.SUPERSEDE.value,
            record=succ_record,
        )

    def _apply_suspend(
        self,
        request: BoundaryRequest,
        source: SourceLifecycle,
        legality: LegalityResult,
        record: RuntimeStoreRecord | None,
    ) -> BoundaryDecision:
        assert record is not None  # legal suspend has a non-terminal active record
        identity = record.identity
        revision = record.row.audit.revision
        prior = prior_state_mutation(
            "TR-033", pre_transition_state=record.row.fsm_state_ref
        )
        fields: dict[str, object] = {
            "workflow_lifecycle": LIFECYCLE_SUSPENDED,
            "owner_lock_active": None,
            "owner_lock_token": None,
            "owner_lock_acquired_at": None,
            "owner_lock_expires_at": None,
            "boundary_event": BoundaryEvent.SUSPEND.value,
            "revision": revision + 1,
        }
        fields.update(prior.as_field_update())
        updated = self._adapter.update(
            identity,
            workflow_fields=fields,
            audit=self._audit(request, identity, "boundary_suspend", revision),
        )
        return self._decision(
            applied=True,
            request=request,
            source=source,
            legality=legality,
            workflow_id=identity.workflow_id,
            boundary_event=BoundaryEvent.SUSPEND.value,
            prior_non_terminal_fsm_state=prior.value,
            record=updated,
        )

    def _apply_resume(
        self,
        request: BoundaryRequest,
        source: SourceLifecycle,
        legality: LegalityResult,
        record: RuntimeStoreRecord | None,
    ) -> BoundaryDecision:
        assert record is not None  # legal resume has a non-terminal suspended record
        identity = record.identity
        revision = record.row.audit.revision
        prior = prior_state_mutation("TR-034", pre_transition_state=None)
        fields: dict[str, object] = {
            "workflow_lifecycle": LIFECYCLE_ACTIVE,
            "boundary_event": BoundaryEvent.RESUME.value,
            "revision": revision + 1,
        }
        fields.update(prior.as_field_update())
        self._adapter.update(
            identity,
            workflow_fields=fields,
            audit=self._audit(request, identity, "boundary_resume", revision),
        )
        # Lifecycle is now active; grant the owner lock via the lock manager so
        # lock token/lease logic is never re-implemented here (§4.5 scenario 2:
        # resume regains the active owner lock).
        self._locks.acquire(identity, request.owner_agent)
        final = self._adapter.read(identity)
        return self._decision(
            applied=True,
            request=request,
            source=source,
            legality=legality,
            workflow_id=identity.workflow_id,
            boundary_event=BoundaryEvent.RESUME.value,
            prior_non_terminal_fsm_state=None,
            record=final,
        )

    def _apply_terminalize(
        self,
        request: BoundaryRequest,
        source: SourceLifecycle,
        legality: LegalityResult,
        record: RuntimeStoreRecord | None,
    ) -> BoundaryDecision:
        assert record is not None  # legal terminalize has a non-terminal record
        identity = record.identity
        revision = record.row.audit.revision
        terminal_state = self._terminal_state(request)
        fields = {
            "workflow_lifecycle": LIFECYCLE_TERMINAL,
            "is_terminal": 1,
            "terminal_state": terminal_state,
            "terminalized_at": self._now_iso(),
            "terminal_reason": TERMINAL_REASON_BY_STATE[terminal_state],
            "owner_lock_active": None,
            "owner_lock_token": None,
            "owner_lock_acquired_at": None,
            "owner_lock_expires_at": None,
            "boundary_event": BoundaryEvent.TERMINALIZE.value,
            "revision": revision + 1,
        }
        updated = self._adapter.update(
            identity,
            workflow_fields=fields,
            audit=self._audit(request, identity, "boundary_terminalize", revision),
        )
        return self._decision(
            applied=True,
            request=request,
            source=source,
            legality=legality,
            workflow_id=identity.workflow_id,
            boundary_event=BoundaryEvent.TERMINALIZE.value,
            record=updated,
        )

    # ----------------------------------------------------------------- #
    # Helpers.
    # ----------------------------------------------------------------- #
    def _terminalize_predecessor(
        self, request: BoundaryRequest, predecessor_id: str, successor_id: str
    ) -> None:
        identity = RuntimeIdentity(
            request.session_id, predecessor_id, request.turn_id
        )
        record = self._adapter.read(identity)
        assert record is not None  # predecessor existed at source resolution
        revision = record.row.audit.revision
        self._adapter.update(
            identity,
            workflow_fields={
                "successor_workflow_id": successor_id,
                "workflow_lifecycle": LIFECYCLE_TERMINAL,
                "is_terminal": 1,
                "terminal_state": None,
                "terminalized_at": self._now_iso(),
                "terminal_reason": "superseded",
                "owner_lock_active": None,
                "owner_lock_token": None,
                "owner_lock_acquired_at": None,
                "owner_lock_expires_at": None,
                "boundary_event": BoundaryEvent.SUPERSEDE.value,
                "revision": revision + 1,
            },
            audit=self._audit(
                request, identity, "boundary_supersede_predecessor", revision
            ),
        )

    def _create(self, identity: RuntimeIdentity, seed: NewWorkflowSeed) -> None:
        self._adapter.create(
            identity,
            row_id=seed.row_id,
            item_id=seed.item_id,
            fsm_state_ref=seed.initial_fsm_state,
            created_by=seed.created_by,
            immutable_fields_hash=seed.immutable_fields_hash,
            workflow_lifecycle=LIFECYCLE_ACTIVE,
        )

    @staticmethod
    def _require_seed(request: BoundaryRequest) -> NewWorkflowSeed:
        if request.new_seed is None:
            raise BoundaryRequestError(
                f"{request.event.value} requires new_seed to allocate a workflow row"
            )
        return request.new_seed

    @staticmethod
    def _terminal_state(request: BoundaryRequest) -> str:
        transition_id = request.transition_id
        if transition_id is not None and is_terminal_transition(transition_id):
            return terminal_state_for(transition_id)
        if request.terminal_state is not None:
            return request.terminal_state
        raise BoundaryRequestError(
            "terminalize requires a terminal transition_id or an explicit terminal_state"
        )

    def _revision(self, identity: RuntimeIdentity) -> int:
        record = self._adapter.read(identity)
        assert record is not None  # caller just created/read this identity
        return record.row.audit.revision

    def _audit(
        self,
        request: BoundaryRequest,
        identity: RuntimeIdentity,
        operation: str,
        revision: int,
    ) -> MutationAudit:
        return MutationAudit(
            actor=request.owner_agent,
            operation=operation,
            operation_id=idempotency_key(
                identity.session_id, identity.workflow_id, identity.turn_id, operation
            ),
            from_revision=revision,
            to_revision=revision + 1,
        )

    def _now_iso(self) -> str:
        return self._clock().strftime(_ISO_FORMAT)

    def _denied(
        self,
        request: BoundaryRequest,
        source: SourceLifecycle,
        legality: LegalityResult,
    ) -> BoundaryDecision:
        return self._decision(
            applied=False, request=request, source=source, legality=legality
        )

    @staticmethod
    def _decision(
        *,
        applied: bool,
        request: BoundaryRequest,
        source: SourceLifecycle,
        legality: LegalityResult,
        workflow_id: str | None = None,
        predecessor_workflow_id: str | None = None,
        successor_workflow_id: str | None = None,
        boundary_event: str | None = None,
        prior_non_terminal_fsm_state: str | None = None,
        record: RuntimeStoreRecord | None = None,
    ) -> BoundaryDecision:
        return BoundaryDecision(
            applied=applied,
            legal=legality.legal,
            event=request.event,
            source=source,
            reason=legality.reason,
            mutation=legality.mutation,
            workflow_id=workflow_id,
            predecessor_workflow_id=predecessor_workflow_id,
            successor_workflow_id=successor_workflow_id,
            boundary_event=boundary_event,
            prior_non_terminal_fsm_state=prior_non_terminal_fsm_state,
            record=record,
        )
