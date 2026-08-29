"""Live decision service — composes the real pipeline into an HTTP handler.

spec015 Phase 8 wiring. The transport layer
(:mod:`helm_controller.transport.http_server`) is policy-agnostic: it calls an
injected ``decision_handler(payload) -> wire_dict`` and echoes the result to the
R2 hook wrapper. Phase 8 retires the placeholder handler and wires the real
chain here:

    raw payload -> :class:`~helm_controller.hooks.pipeline.DecisionPipeline`
    (parse -> :class:`~helm_controller.hooks.envelope_assembler.EnvelopeAssembler`
    with role resolved through the real
    :class:`~helm_controller.policy.registry.AgentRoleRegistry` -> policy/FSM/
    gates/invariants/pre-send) -> internal :class:`Decision` ->
    :func:`~helm_controller.hooks.response_adapter.to_wire` -> VS Code-native JSON.

The long-lived dependencies (registry, store adapter, agent stack, assembler,
pipeline) are built ONCE at server startup by :func:`build_pipeline`; each
``sqlite3`` connection is still opened per request inside the adapters
(connection-per-request, WAL), so no connection crosses a ThreadingHTTPServer
thread boundary.

Fail-closed posture: the transport already converts an exception in the handler
into an HTTP 500 deny, but this handler catches first so the controller emits the
response adapter's defensive cross-family deny (a wire shape VS Code honors on
both the permission and block fields) rather than the transport's bare internal
deny. An internal error therefore never fails open.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from helm_controller.config import ControllerConfig
from helm_controller.hooks.agent_stack import AgentStackStore
from helm_controller.hooks.envelope_assembler import EnvelopeAssembler
from helm_controller.hooks.pipeline import DecisionPipeline, PipelineRequest
from helm_controller.hooks.response_adapter import to_wire
from helm_controller.policy.registry import AgentRoleRegistry
from helm_controller.store.adapter import RuntimeStoreAdapter
from helm_controller.transport.http_server import DecisionHandler

_LOGGER = logging.getLogger("helm_controller.hooks.decision_service")


def build_pipeline(
    workspace: Path,
    config: ControllerConfig,
    *,
    registry: AgentRoleRegistry | None = None,
) -> DecisionPipeline:
    """Construct the long-lived decision pipeline with real dependencies.

    Resolves agent roles through the bundled ``agent_roles.json`` registry so
    ``actor.active_role`` is a real policy role (never ``UNKNOWN`` for a
    registered agent). The store adapter and agent stack share the one runtime
    database file under the workspace.
    """
    registry = registry or AgentRoleRegistry()
    store = RuntimeStoreAdapter.from_config(workspace, config)
    stack = AgentStackStore(workspace / config.store.db_path)
    assembler = EnvelopeAssembler(
        store, stack, workspace, role_resolver=registry.resolve_role
    )
    return DecisionPipeline(assembler, role_registry=registry)


def make_decision_handler(pipeline: DecisionPipeline) -> DecisionHandler:
    """Adapt a :class:`DecisionPipeline` to the transport's handler contract."""

    def handler(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            result = pipeline.evaluate(PipelineRequest(payload=payload))
        except Exception:
            _LOGGER.exception("Decision pipeline raised; failing closed.")
            return to_wire(None, None)
        return to_wire(result.hook_event, result.decision)

    return handler


def build_decision_handler(
    workspace: Path,
    config: ControllerConfig,
    *,
    registry: AgentRoleRegistry | None = None,
) -> DecisionHandler:
    """Build the real pipeline and wrap it as a transport decision handler."""
    return make_decision_handler(
        build_pipeline(workspace, config, registry=registry)
    )
