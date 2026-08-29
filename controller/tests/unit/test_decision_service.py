"""Tests for the Phase 8 live decision service wiring (spec015).

Exercises the composition root that replaces the retired placeholder handler:
``build_pipeline`` constructs the real pipeline with the bundled
``agent_roles.json`` registry, and ``make_decision_handler`` adapts a pipeline
verdict into the VS Code-native wire shape, failing closed on any internal
error. The allow/deny cases prove the wired ``role_resolver`` resolves a REAL
policy role (orchestrator) through the registry — not the ``UNKNOWN`` default
the assembler ships with.
"""

from __future__ import annotations

from pathlib import Path

from helm_controller.config import ControllerConfig
from helm_controller.hooks.agent_stack import AgentStackStore
from helm_controller.hooks.decision_service import (
    build_decision_handler,
    build_pipeline,
    make_decision_handler,
)
from helm_controller.policy.registry import AgentRoleRegistry
from helm_controller.store.adapter import RuntimeStoreAdapter
from helm_controller.store.identity import RuntimeIdentity

_SESSION = "sess-wire"
_WF = "wf-wire"


def _seed(workspace: Path, config: ControllerConfig) -> None:
    db_path = workspace / config.store.db_path
    store = RuntimeStoreAdapter(db_path)
    stack = AgentStackStore(db_path)
    store.create(
        RuntimeIdentity(_SESSION, _WF, "0"),
        row_id="BBR-000001",
        item_id="item-1",
        fsm_state_ref="ST-000",
        created_by="ARTHUR",
        immutable_fields_hash="h",
    )
    stack.set_active_workflow(_SESSION, _WF)


def _payload(tool_name: str) -> dict:
    return {
        "hookEventName": "PreToolUse",
        "sessionId": _SESSION,
        "transcript_path": "/tmp/t.jsonl",
        "timestamp": "2026-05-31T12:00:00Z",
        "tool_name": tool_name,
        "tool_use_id": "tu-1",
        "tool_input": {},
    }


def test_build_pipeline_resolves_real_roles(tmp_path: Path) -> None:
    config = ControllerConfig()
    pipeline = build_pipeline(tmp_path, config)
    # The wired registry resolves registered agents to real roles, not UNKNOWN.
    assert pipeline._roles.resolve_role("ARTHUR") == "orchestrator"
    assert pipeline._roles.resolve_role("FORGE") == "implementer"


def test_handler_real_allow_emits_permission_allow(tmp_path: Path) -> None:
    config = ControllerConfig()
    _seed(tmp_path, config)
    handler = build_decision_handler(tmp_path, config)
    # ARTHUR (orchestrator) reading a file -> read class -> ALLOW. An UNKNOWN
    # role would DENY read, so an allow proves the role resolved to orchestrator.
    wire = handler(_payload("read_file"))
    hso = wire["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "allow"


def test_handler_real_deny_emits_permission_deny(tmp_path: Path) -> None:
    config = ControllerConfig()
    _seed(tmp_path, config)
    handler = build_decision_handler(tmp_path, config)
    # ARTHUR (orchestrator) file_mutation -> DENY (PC-001) through the matrix.
    wire = handler(_payload("create_file"))
    hso = wire["hookSpecificOutput"]
    assert hso["permissionDecision"] == "deny"
    assert "PC-001" in hso["permissionDecisionReason"]


def test_handler_pc004_deny_when_identity_unresolvable(tmp_path: Path) -> None:
    # No seeded workflow -> envelope assembler emits PC-004; the wired handler
    # renders it as a PreToolUse permission deny (never a silent allow).
    config = ControllerConfig()
    handler = build_decision_handler(tmp_path, config)
    wire = handler(_payload("read_file"))
    assert wire["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "PC-004" in wire["hookSpecificOutput"]["permissionDecisionReason"]


def test_handler_fails_closed_on_pipeline_exception() -> None:
    class _Boom:
        def evaluate(self, _request: object) -> object:
            raise RuntimeError("pipeline blew up")

    handler = make_decision_handler(_Boom())
    wire = handler({"hookEventName": "PreToolUse", "sessionId": "s"})
    # Defensive cross-family deny: honored on both permission and block fields.
    assert wire["decision"] == "block"
    assert wire["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_build_decision_handler_accepts_injected_registry(tmp_path: Path) -> None:
    config = ControllerConfig()
    _seed(tmp_path, config)
    registry = AgentRoleRegistry()
    handler = build_decision_handler(tmp_path, config, registry=registry)
    wire = handler(_payload("read_file"))
    assert wire["hookSpecificOutput"]["permissionDecision"] == "allow"
