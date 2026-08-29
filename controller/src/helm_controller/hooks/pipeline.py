"""Decision pipeline — orchestrates Phases 3-7 into one allow/deny/ask verdict.

spec015 Task 8.1. For each hook event the pipeline runs the policy stages in the
order mandated by boundary contract §6.2 and plan Task 8.1:

  1. parse the raw payload (:mod:`helm_controller.hooks.parsers`),
  2. assemble the validated envelope (Phase 3 ``EnvelopeAssembler``; a ``PC-004``
     identity failure short-circuits here),
  3. lifecycle boundary evaluation + APPLY-to-store BEFORE any FSM check — the
     FSM's legal transitions depend on committed lifecycle state, so an
     uncommitted ``new`` boundary would make the FSM see stale state and deny
     spuriously (plan Task 8.1 ordering rationale). An illegal boundary command
     fails ``CHK-003`` and routes to ST-903 (POL-044),
  4. role -> role-tool matrix -> conditional checks (tool-bearing events only),
  5. FSM transition legality (Phase 5),
  6. BG blackboard gates ascending fail-fast (Phase 6),
  7. INV invariants, lowest-id reported (Phase 6),
  8. CHK pre-send checks ascending fail-fast (Phase 6),
  9. emit the §6.2 decision: ``illegal -> deny`` / ``gate fail -> deny`` /
     ``missing checkpoint -> ask`` / ``else -> allow``.

The snapshot, FSM event, blackboard, and any boundary request are injected on
the :class:`PipelineRequest` (the Phase 9 replay harness supplies them from
recorded fixtures; Phase 8 tests build them with the conftest factories). The
pipeline emits the INTERNAL :class:`Decision`; the VS Code-native wire shape is
the response adapter's job (Task 8.2), invoked by the decision emitter.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from helm_controller.contracts.blackboard import BlackboardRow
from helm_controller.contracts.decision import Decision
from helm_controller.contracts.envelope import Envelope
from helm_controller.contracts.snapshot import Snapshot
from helm_controller.fsm.evaluator import evaluate as evaluate_transition
from helm_controller.fsm.events import Event
from helm_controller.fsm.states import State
from helm_controller.gates.bg_evaluator import evaluate_blackboard_gates
from helm_controller.gates.presend_checks import run_presend_checks
from helm_controller.hooks.envelope_assembler import EnvelopeAssembler
from helm_controller.hooks.parsers import HookParseError, ParsedHook, parse
from helm_controller.invariants.inv_evaluator import evaluate_invariants
from helm_controller.lifecycle.evaluator import (
    BoundaryRequest,
    LifecycleBoundaryEvaluator,
)
from helm_controller.policy.conditional_checks import run_conditional_checks
from helm_controller.policy.matrix import Verdict
from helm_controller.policy.matrix import evaluate as evaluate_matrix
from helm_controller.policy.registry import AgentRoleRegistry
from helm_controller.policy.tool_classes import ToolClassMap

#: Illegal boundary commands fail CHK-003 and route to ST-903 (POL-044), the
#: same canonical code an illegal FSM transition uses; the reason text keeps the
#: two human-distinguishable.
BOUNDARY_ILLEGAL_REASON_ID = "CHK-003"
PRE_SEND_BLOCKED_STATE = "ST-903"
PARSE_FAILURE_REASON_ID = "PC-004"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class PipelineRequest:
    """One hook invocation plus the replay-injected evaluation context."""

    payload: object
    snapshot: Snapshot | None = None
    event: Event | None = None
    blackboard: BlackboardRow | None = None
    boundary_request: BoundaryRequest | None = None
    checkpoint_required: bool = False
    checkpoint_reason_id: str = "PC-006"
    checkpoint_reason: str = "required user checkpoint missing"


@dataclass(frozen=True)
class PipelineResult:
    """The pipeline's verdict: the hook event plus the internal decision."""

    hook_event: str
    decision: Decision


class DecisionPipeline:
    """Runs the ordered policy stages and returns the internal decision."""

    def __init__(
        self,
        assembler: EnvelopeAssembler,
        *,
        lifecycle_evaluator: LifecycleBoundaryEvaluator | None = None,
        tool_class_map: ToolClassMap | None = None,
        role_registry: AgentRoleRegistry | None = None,
        clock=_utcnow,
    ) -> None:
        self._assembler = assembler
        self._lifecycle = lifecycle_evaluator
        self._tool_classes = tool_class_map or ToolClassMap()
        self._roles = role_registry or AgentRoleRegistry()
        self._clock = clock

    def evaluate(self, request: PipelineRequest) -> PipelineResult:
        """Run the ordered stages and return the first decisive verdict."""
        try:
            parsed = parse(request.payload)
        except HookParseError as exc:
            return self._parse_failure(request.payload, exc)
        assembly = self._assembler.assemble(parsed)
        if not assembly.ok:
            return PipelineResult(parsed.hook_event, assembly.deny)
        envelope = assembly.envelope
        decision = (
            self._boundary_stage(request)
            or self._policy_stage(parsed, envelope, request)
            or self._fsm_stage(request)
            or self._gate_stage(request)
            or self._invariant_stage(request)
            or self._presend_stage(request)
            or self._final_decision(request)
        )
        return PipelineResult(parsed.hook_event, decision)

    # ---- stages ----------------------------------------------------------- #
    def _boundary_stage(self, request: PipelineRequest) -> Decision | None:
        if request.boundary_request is None or self._lifecycle is None:
            return None
        boundary = self._lifecycle.evaluate(request.boundary_request)
        if boundary.legal:
            return None
        return Decision(
            decision="deny",
            reason_id=BOUNDARY_ILLEGAL_REASON_ID,
            reason=f"illegal boundary transition: {boundary.reason}",
            state_after=PRE_SEND_BLOCKED_STATE,
        )

    def _policy_stage(
        self, parsed: ParsedHook, envelope: Envelope, request: PipelineRequest
    ) -> Decision | None:
        tool_name = parsed.tool_name
        if tool_name is None:
            return None
        role = envelope.actor.active_role
        tool_class = self._tool_classes.classify(tool_name).policy_class
        result = evaluate_matrix(role, tool_class)
        if result.verdict is Verdict.DENY:
            return Decision(
                decision="deny", reason_id=result.reason_id, reason=result.reason
            )
        if result.verdict is Verdict.COND:
            cc = run_conditional_checks(
                result.conditional_checks,
                role=role,
                tool_name=tool_name,
                tool_input=parsed.tool_input,
                workspace_root=envelope.workspace_root,
                tool_class_map=self._tool_classes,
                resolve_role=self._roles.resolve_role,
            )
            if not cc.passed:
                return Decision(
                    decision="deny", reason_id=cc.reason_id, reason=cc.reason
                )
        return None

    def _fsm_stage(self, request: PipelineRequest) -> Decision | None:
        if request.snapshot is None or request.event is None:
            return None
        state_before = State(request.snapshot.state_before)
        result = evaluate_transition(state_before, request.event, request.snapshot)
        if result.legal:
            return None
        return result.decision

    def _gate_stage(self, request: PipelineRequest) -> Decision | None:
        if request.snapshot is None or request.blackboard is None:
            return None
        bg = evaluate_blackboard_gates(
            request.snapshot, request.blackboard, now=self._clock()
        )
        if bg.passed:
            return None
        return bg.decision

    def _invariant_stage(self, request: PipelineRequest) -> Decision | None:
        if request.snapshot is None or request.blackboard is None:
            return None
        inv = evaluate_invariants(
            request.snapshot, request.blackboard, self._roles.resolve_role
        )
        if inv.passed:
            return None
        return inv.decision

    def _presend_stage(self, request: PipelineRequest) -> Decision | None:
        if request.snapshot is None:
            return None
        ps = run_presend_checks(request.snapshot)
        if ps.passed:
            return None
        return ps.decision

    def _final_decision(self, request: PipelineRequest) -> Decision:
        if request.checkpoint_required:
            return Decision(
                decision="ask",
                reason_id=request.checkpoint_reason_id,
                reason=request.checkpoint_reason,
            )
        return Decision(
            decision="allow", reason_id="", reason="all policy checks passed"
        )

    def _parse_failure(self, payload: object, exc: HookParseError) -> PipelineResult:
        hook_event = ""
        if isinstance(payload, dict):
            raw = payload.get("hookEventName")
            if isinstance(raw, str):
                hook_event = raw
        decision = Decision(
            decision="deny",
            reason_id=PARSE_FAILURE_REASON_ID,
            reason=f"hook payload parse failure: {exc}",
        )
        return PipelineResult(hook_event, decision)
