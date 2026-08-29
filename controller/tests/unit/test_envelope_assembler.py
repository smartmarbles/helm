"""Tests for the envelope assembler (spec015 Task 3.3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from helm_controller.contracts.envelope import Envelope
from helm_controller.hooks import envelope_assembler as ea_module
from helm_controller.hooks.agent_stack import AgentStackStore
from helm_controller.hooks.envelope_assembler import (
    EnvelopeAssembler,
    EnvelopeAssemblyError,
    PC_004,
    ROOT_AGENT,
)
from helm_controller.hooks.parsers import ParsedHook
from helm_controller.store.adapter import RuntimeStoreAdapter
from helm_controller.store.identity import RuntimeIdentity

_SESSION = "sess-1"
_WF = "wf-1"
_TS = "2026-05-31T12:00:00Z"


def _parsed(event: str, **kwargs) -> ParsedHook:
    base = dict(
        hook_event=event,
        session_id=_SESSION,
        timestamp=_TS,
        cwd=None,
        transcript_path="/tmp/t.jsonl",
    )
    base.update(kwargs)
    return ParsedHook(**base)


def _build(tmp_path: Path, **kwargs):
    store = RuntimeStoreAdapter(tmp_path / "store.db")
    stack = AgentStackStore(tmp_path / "store.db")
    assembler = EnvelopeAssembler(store, stack, tmp_path, **kwargs)
    return store, stack, assembler


def _seed_workflow(store: RuntimeStoreAdapter, turn_id: str = "0") -> None:
    store.create(
        RuntimeIdentity(_SESSION, _WF, turn_id),
        row_id="BBR-000001",
        item_id="item-1",
        fsm_state_ref="ST-001",
        created_by="ARTHUR",
        immutable_fields_hash="hash-1",
    )


# --------------------------------------------------------------------------- #
# pre-workflow events: null workflow is acceptable (no PC-004)
# --------------------------------------------------------------------------- #
def test_session_start_assembles_without_workflow(tmp_path: Path) -> None:
    _store, _stack, assembler = _build(tmp_path)
    result = assembler.assemble(_parsed("SessionStart", source="new"))
    assert result.ok
    env = result.envelope
    assert isinstance(env, Envelope)
    assert env.hook_event == "SessionStart"
    assert env.workflow.workflow_id is None
    assert env.blackboard.row_present is False
    assert env.actor.active_agent == ROOT_AGENT
    assert env.actor.active_role == "UNKNOWN"
    assert env.actor.subagent_id is None
    assert set(env.blackboard.gates) == {
        "BG-001",
        "BG-002",
        "BG-003",
        "BG-004",
        "BG-005",
        "BG-006",
    }
    assert all(v is None for v in env.blackboard.gates.values())


def test_user_prompt_submit_increments_turn(tmp_path: Path) -> None:
    _store, stack, assembler = _build(tmp_path)
    result = assembler.assemble(_parsed("UserPromptSubmit", prompt="hi"))
    assert result.ok
    assert result.envelope.workflow.turn_id == "1"
    assert stack.current_turn(_SESSION) == 1


def test_pre_compact_assembles_without_workflow(tmp_path: Path) -> None:
    _store, _stack, assembler = _build(tmp_path)
    result = assembler.assemble(_parsed("PreCompact", trigger="auto"))
    assert result.ok
    assert result.envelope.hook_event == "PreCompact"


# --------------------------------------------------------------------------- #
# workflow-requiring events: PC-004 when identity unresolvable
# --------------------------------------------------------------------------- #
def test_pre_tool_use_without_active_workflow_denies_pc004(tmp_path: Path) -> None:
    _store, _stack, assembler = _build(tmp_path)
    result = assembler.assemble(
        _parsed("PreToolUse", tool_name="read_file", tool_use_id="tu-1")
    )
    assert not result.ok
    assert result.envelope is None
    assert result.deny is not None
    assert result.deny.decision == "deny"
    assert result.deny.reason_id == PC_004


def test_workflow_pointer_set_but_record_missing_denies_pc004(tmp_path: Path) -> None:
    _store, stack, assembler = _build(tmp_path)
    stack.set_active_workflow(_SESSION, _WF)  # pointer set, but no store record
    result = assembler.assemble(_parsed("Stop", stop_hook_active=False))
    assert not result.ok
    assert result.deny.reason_id == PC_004


# --------------------------------------------------------------------------- #
# workflow-requiring events: happy path with a seeded workflow
# --------------------------------------------------------------------------- #
def test_pre_tool_use_happy_path_with_workflow(tmp_path: Path) -> None:
    store, stack, assembler = _build(tmp_path)
    _seed_workflow(store)
    stack.set_active_workflow(_SESSION, _WF)
    result = assembler.assemble(
        _parsed(
            "PreToolUse",
            tool_name="read_file",
            tool_use_id="tu-1",
            tool_input={"path": "x"},
        )
    )
    assert result.ok
    env = result.envelope
    assert env.workflow.workflow_id == _WF
    assert env.workflow.state_before == "ST-001"
    assert env.blackboard.row_present is True
    assert env.blackboard.row_id == "BBR-000001"
    assert env.blackboard.fsm_state_ref == "ST-001"
    assert env.tool_attempt.tool_name == "read_file"
    assert env.tool_attempt.tool_use_id == "tu-1"
    assert env.tool_attempt.tool_input == {"path": "x"}
    assert env.tool_attempt.tool_response is None


def test_post_tool_use_maps_tool_response(tmp_path: Path) -> None:
    store, stack, assembler = _build(tmp_path)
    _seed_workflow(store)
    stack.set_active_workflow(_SESSION, _WF)
    result = assembler.assemble(
        _parsed(
            "PostToolUse",
            tool_name="read_file",
            tool_use_id="tu-1",
            tool_input={"path": "x"},
            tool_response={"ok": True},
        )
    )
    assert result.ok
    assert result.envelope.tool_attempt.tool_response == {"ok": True}


def test_stop_happy_path_with_workflow(tmp_path: Path) -> None:
    store, stack, assembler = _build(tmp_path)
    _seed_workflow(store)
    stack.set_active_workflow(_SESSION, _WF)
    result = assembler.assemble(_parsed("Stop", stop_hook_active=True))
    assert result.ok
    assert result.envelope.hook_event == "Stop"


# --------------------------------------------------------------------------- #
# active-agent resolution across SubagentStart / SubagentStop
# --------------------------------------------------------------------------- #
def test_subagent_start_pushes_and_reports_started_agent(tmp_path: Path) -> None:
    store, stack, assembler = _build(tmp_path)
    _seed_workflow(store)
    stack.set_active_workflow(_SESSION, _WF)
    result = assembler.assemble(
        _parsed("SubagentStart", agent_id="sub-1", agent_type="FORGE")
    )
    assert result.ok
    assert result.envelope.actor.active_agent == "FORGE"
    assert result.envelope.actor.subagent_id == "sub-1"
    assert stack.depth(_SESSION) == 1


def test_subagent_start_without_agent_type_falls_back_to_root(tmp_path: Path) -> None:
    store, stack, assembler = _build(tmp_path)
    _seed_workflow(store)
    stack.set_active_workflow(_SESSION, _WF)
    result = assembler.assemble(_parsed("SubagentStart", agent_id="sub-1"))
    assert result.ok
    assert result.envelope.actor.active_agent == ROOT_AGENT
    assert stack.depth(_SESSION) == 1


def test_subagent_stop_reports_stopping_agent_then_pops(tmp_path: Path) -> None:
    store, stack, assembler = _build(tmp_path)
    _seed_workflow(store)
    stack.set_active_workflow(_SESSION, _WF)
    stack.push(_SESSION, "FORGE", subagent_id="sub-1")
    result = assembler.assemble(
        _parsed("SubagentStop", agent_id="sub-1", stop_hook_active=False)
    )
    assert result.ok
    assert result.envelope.actor.active_agent == "FORGE"
    assert stack.depth(_SESSION) == 0


def test_subagent_stop_on_empty_stack_reports_root(tmp_path: Path) -> None:
    store, stack, assembler = _build(tmp_path)
    _seed_workflow(store)
    stack.set_active_workflow(_SESSION, _WF)
    result = assembler.assemble(_parsed("SubagentStop", stop_hook_active=False))
    assert result.ok
    assert result.envelope.actor.active_agent == ROOT_AGENT


def test_pre_tool_use_reports_top_of_stack_agent(tmp_path: Path) -> None:
    store, stack, assembler = _build(tmp_path)
    _seed_workflow(store)
    stack.set_active_workflow(_SESSION, _WF)
    stack.push(_SESSION, "SAGE", subagent_id="sub-a")
    stack.push(_SESSION, "FORGE", subagent_id="sub-b")
    result = assembler.assemble(_parsed("PreToolUse", tool_name="t", tool_use_id="u"))
    assert result.ok
    assert result.envelope.actor.active_agent == "FORGE"
    assert result.envelope.actor.subagent_id == "sub-b"


# --------------------------------------------------------------------------- #
# injected role resolver
# --------------------------------------------------------------------------- #
def test_injected_role_resolver_is_used(tmp_path: Path) -> None:
    roles = {"ARTHUR": "orchestrator"}
    _store, _stack, assembler = _build(
        tmp_path, role_resolver=lambda name: roles.get(name, "UNKNOWN")
    )
    result = assembler.assemble(_parsed("SessionStart", source="new"))
    assert result.ok
    assert result.envelope.actor.active_role == "orchestrator"


# --------------------------------------------------------------------------- #
# timestamp fallback + validation failure
# --------------------------------------------------------------------------- #
def test_missing_timestamp_falls_back_to_clock(tmp_path: Path) -> None:
    from datetime import datetime, timezone

    fixed = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    _store, _stack, assembler = _build(tmp_path, clock=lambda: fixed)
    result = assembler.assemble(_parsed("SessionStart", source="new", timestamp=None))
    assert result.ok
    assert result.envelope.timestamp == "2026-01-02T03:04:05Z"


def test_missing_timestamp_default_clock_emits_iso(tmp_path: Path) -> None:
    _store, _stack, assembler = _build(tmp_path)  # default clock (_utcnow)
    result = assembler.assemble(_parsed("SessionStart", source="new", timestamp=None))
    assert result.ok
    ts = result.envelope.timestamp
    assert ts.endswith("Z") and ts.startswith("20")


def test_invalid_envelope_raises_assembly_error(tmp_path: Path, monkeypatch) -> None:
    from helm_controller.contracts.validator import Contract, ContractValidationError

    _store, _stack, assembler = _build(tmp_path)

    def _raise(*_args, **_kwargs):
        raise ContractValidationError(Contract.ENVELOPE, ["forced failure"])

    monkeypatch.setattr(ea_module, "validate", _raise)
    with pytest.raises(EnvelopeAssemblyError, match="failed validation"):
        assembler.assemble(_parsed("SessionStart", source="new"))


# --------------------------------------------------------------------------- #
# result wrapper
# --------------------------------------------------------------------------- #
def test_assembly_ok_property_reflects_state(tmp_path: Path) -> None:
    _store, _stack, assembler = _build(tmp_path)
    ok_result = assembler.assemble(_parsed("SessionStart", source="new"))
    deny_result = assembler.assemble(_parsed("PreToolUse", tool_name="t"))
    assert ok_result.ok is True
    assert deny_result.ok is False
