"""Envelope assembler — parsed hook + store/stack lookups -> validated envelope.

spec015 Task 3.3. This is the join point of the Phase 3 hook adapter: it takes
a :class:`~helm_controller.hooks.parsers.ParsedHook` (Task 3.1), applies the
per-session active-agent stack and routing pointers
(:class:`~helm_controller.hooks.agent_stack.AgentStackStore`, Task 3.2), reads
the workflow-scoped record from the runtime store
(:class:`~helm_controller.store.adapter.RuntimeStoreAdapter`, Task 2.2), and
produces one schema-validated
:class:`~helm_controller.contracts.envelope.Envelope` per hook invocation.

Identity & fail-closed (``PC-004``). The runtime identity tuple is
``(session_id, workflow_id, turn_id)``. ``session_id`` always arrives on the
payload and ``turn_id`` is read from the store's prompt-turn counter (NEVER the
payload — Watch Out #18). ``workflow_id`` is resolved through the session's
active-workflow routing pointer. The pre-workflow events (``SessionStart``,
``UserPromptSubmit``, ``PreCompact``) legitimately precede any workflow, so a
null pointer is acceptable for them and the envelope carries null workflow
context. For every workflow-scoped event (``PreToolUse``, ``PostToolUse``,
``SubagentStart``, ``SubagentStop``, ``Stop``) an unresolvable workflow identity
is the controller-side "can't establish identity" signal: the assembler emits a
``PC-004`` deny in the INTERNAL ``allow``/``deny``/``ask`` vocabulary (Plan
Decisions §D2). The VS Code-native wire shape is the Task 8.2 adapter's job, NOT
this module's.

Role resolution is the Phase 4 registry's job. Until it lands, an injectable
``role_resolver`` (default: everything resolves to ``UNKNOWN``) keeps the
schema's required ``actor.active_role`` satisfied without reaching into an
unbuilt phase.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from helm_controller.contracts.decision import Decision
from helm_controller.contracts.envelope import (
    Actor,
    BlackboardContext,
    Envelope,
    ToolAttempt,
    WorkflowContext,
)
from helm_controller.contracts.validator import (
    Contract,
    ContractValidationError,
    validate,
)
from helm_controller.hooks.agent_stack import AgentStackStore
from helm_controller.hooks.parsers import ParsedHook
from helm_controller.store.adapter import RuntimeStoreAdapter
from helm_controller.store.identity import RuntimeIdentity

POLICY_VERSION = "1.0.0"
PC_004 = "PC-004"
ROOT_AGENT = "ARTHUR"
UNKNOWN_ROLE = "UNKNOWN"

#: Events that legitimately precede a workflow; a null ``workflow_id`` for these
#: is NOT an identity failure (so ``PC-004`` MUST NOT fire on a fresh session).
_PRE_WORKFLOW_EVENTS: frozenset[str] = frozenset(
    {"SessionStart", "UserPromptSubmit", "PreCompact"}
)

_GATE_IDS: tuple[str, ...] = (
    "BG-001",
    "BG-002",
    "BG-003",
    "BG-004",
    "BG-005",
    "BG-006",
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _default_role_resolver(_agent_name: str) -> str:
    return UNKNOWN_ROLE


class EnvelopeAssemblyError(RuntimeError):
    """Raised when the assembler produces a schema-invalid envelope (a bug)."""


@dataclass(frozen=True)
class EnvelopeAssembly:
    """Result of one assembly: exactly one of ``envelope`` / ``deny`` is set."""

    envelope: Envelope | None
    deny: Decision | None

    @property
    def ok(self) -> bool:
        return self.envelope is not None


class EnvelopeAssembler:
    """Builds one validated envelope (or a ``PC-004`` deny) per parsed hook."""

    def __init__(
        self,
        store: RuntimeStoreAdapter,
        stack: AgentStackStore,
        workspace_root: Path,
        *,
        role_resolver: Callable[[str], str] | None = None,
        root_agent: str = ROOT_AGENT,
        policy_version: str = POLICY_VERSION,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._store = store
        self._stack = stack
        self._workspace_root = workspace_root
        self._role_resolver = role_resolver or _default_role_resolver
        self._root_agent = root_agent
        self._policy_version = policy_version
        self._clock = clock

    def assemble(self, parsed: ParsedHook) -> EnvelopeAssembly:
        """Assemble the envelope for ``parsed`` or return a ``PC-004`` deny."""
        session_id = parsed.session_id
        event = parsed.hook_event

        turn_id = str(self._resolve_turn(session_id, event))
        active_frame = self._resolve_active_agent(session_id, event, parsed)

        workflow_id = self._stack.active_workflow_id(session_id)
        if workflow_id is None:
            if event not in _PRE_WORKFLOW_EVENTS:
                return self._pc004(event, "no active workflow for session")
            record = None
        else:
            identity = RuntimeIdentity(session_id, workflow_id, turn_id)
            record = self._store.read(identity)
            if record is None:
                return self._pc004(event, "active workflow not found in store")

        envelope = Envelope(
            policy_version=self._policy_version,
            hook_event=event,
            timestamp=parsed.timestamp or self._now_iso(),
            session_id=session_id,
            workspace_root=str(self._workspace_root),
            transcript_path=parsed.transcript_path,
            actor=self._build_actor(active_frame),
            tool_attempt=ToolAttempt(
                tool_name=parsed.tool_name,
                tool_use_id=parsed.tool_use_id,
                tool_input=parsed.tool_input,
                tool_response=parsed.tool_response,
            ),
            workflow=self._build_workflow(workflow_id, turn_id, record),
            blackboard=self._build_blackboard(record),
        )
        try:
            validate(envelope.to_dict(), Contract.ENVELOPE)
        except ContractValidationError as exc:
            raise EnvelopeAssemblyError(
                f"assembled envelope for {event} failed validation: {exc}"
            ) from exc
        return EnvelopeAssembly(envelope=envelope, deny=None)

    # ---- internals -------------------------------------------------------- #
    def _resolve_turn(self, session_id: str, event: str) -> int:
        if event == "UserPromptSubmit":
            return self._stack.increment_turn(session_id)
        return self._stack.current_turn(session_id)

    def _resolve_active_agent(self, session_id, event, parsed):
        if event == "SubagentStart":
            self._stack.push(
                session_id,
                parsed.agent_type or self._root_agent,
                subagent_id=parsed.agent_id,
            )
            return self._stack.current(session_id)
        if event == "SubagentStop":
            active = self._stack.current(session_id)
            self._stack.pop(session_id)
            return active
        return self._stack.current(session_id)

    def _build_actor(self, active_frame) -> Actor:
        if active_frame is None:
            active_agent = self._root_agent
            subagent_id = None
        else:
            active_agent = active_frame.agent_type
            subagent_id = active_frame.subagent_id
        return Actor(
            active_agent=active_agent,
            active_role=self._role_resolver(active_agent),
            subagent_id=subagent_id,
        )

    @staticmethod
    def _build_workflow(workflow_id, turn_id, record) -> WorkflowContext:
        state_before = record.row.fsm_state_ref if record is not None else None
        return WorkflowContext(
            workflow_id=workflow_id,
            turn_id=turn_id,
            state_before=state_before,
            selected_path=None,
            explicit_path=None,
            doc_type=None,
            open_question_count=None,
            user_choice=None,
            approval_prompted=None,
        )

    @staticmethod
    def _build_blackboard(record) -> BlackboardContext:
        if record is None:
            return BlackboardContext(
                row_present=False,
                row_schema_valid=None,
                row_id=None,
                lifecycle_stage=None,
                fsm_state_ref=None,
                required_gates_passed=None,
                gates={gate_id: None for gate_id in _GATE_IDS},
            )
        row = record.row
        return BlackboardContext(
            row_present=row.row_present,
            row_schema_valid=row.row_schema_valid,
            row_id=row.row_id,
            lifecycle_stage=row.lifecycle_stage,
            fsm_state_ref=row.fsm_state_ref,
            required_gates_passed=row.required_gates_passed,
            gates={gate_id: row.gates.get(gate_id) for gate_id in _GATE_IDS},
        )

    def _pc004(self, event: str, detail: str) -> EnvelopeAssembly:
        return EnvelopeAssembly(
            envelope=None,
            deny=Decision(
                decision="deny",
                reason_id=PC_004,
                reason=f"cannot establish runtime identity for {event}: {detail}",
            ),
        )

    def _now_iso(self) -> str:
        return self._clock().strftime("%Y-%m-%dT%H:%M:%SZ")
