"""Round-trip and field-access tests for the four contract dataclasses."""

from __future__ import annotations

from helm_controller.contracts.blackboard import (
    Audit,
    BlackboardRow,
    OwnerLock,
    Terminal,
)
from helm_controller.contracts.decision import Decision
from helm_controller.contracts.envelope import (
    Actor,
    BlackboardContext,
    Envelope,
    ToolAttempt,
    WorkflowContext,
)
from helm_controller.contracts.snapshot import Presend, Snapshot, ToolCalls


def _snapshot_dict() -> dict:
    return {
        "session_id": "s",
        "workflow_id": "w",
        "session_active_workflow_id": None,
        "predecessor_workflow_id": None,
        "successor_workflow_id": None,
        "workflow_lifecycle_before": "non_terminal_active",
        "workflow_lifecycle_after": "non_terminal_active",
        "turn_id": "t",
        "state_before": "ST-001",
        "state_after": "ST-002",
        "prior_non_terminal_fsm_state": None,
        "owner_before": "orchestrator",
        "owner_after": "orchestrator",
        "event": "EV-001",
        "boundary_event": None,
        "selected_path": None,
        "explicit_path": None,
        "doc_type": None,
        "open_question_count": 0,
        "pending_interrupt": "none",
        "actions": ["AC-001"],
        "outbound_sender": "orchestrator",
        "outbound_message_type": "status",
        "prompt_options": [],
        "user_choice": None,
        "approval_prompted": False,
        "open_question_protocol_resolved": False,
        "delegation_claimed": False,
        "dispatch_payload_keys": [],
        "phase_execution_started": False,
        "suppressed_action_ids": [],
        "tool_calls": {"runSubagent": 0},
        "presend": {"executed": True, "result": "pass", "failed_check": None},
        "output_paths": [],
    }


def _blackboard_dict() -> dict:
    gates = {f"BG-00{n}": "pass" for n in range(1, 7)}
    return {
        "row_present": True,
        "row_schema_valid": True,
        "row_id": "BBR-000001",
        "session_id": "s",
        "workflow_id": "w",
        "predecessor_workflow_id": None,
        "successor_workflow_id": None,
        "item_id": "i",
        "lifecycle_stage": "intake",
        "workflow_lifecycle": "non_terminal_active",
        "fsm_state_ref": "ST-001",
        "prior_non_terminal_fsm_state": None,
        "owner_lock": {
            "active": None,
            "lock_token": None,
            "acquired_at": None,
            "expires_at": None,
            "is_stale": False,
            "active_lock_count": 0,
        },
        "gates": gates,
        "required_gates_passed": True,
        "terminal": {
            "is_terminal": False,
            "terminal_state": None,
            "terminalized_at": None,
            "terminal_reason": None,
        },
        "audit": {
            "created_at": "2026-05-31T00:00:00Z",
            "created_by": "ARTHUR",
            "revision": 1,
            "immutable_fields_hash": "h",
            "audit_fields_mutated": False,
        },
        "mutation_attempt_keys": [],
    }


def _envelope_dict() -> dict:
    gates = {f"BG-00{n}": "pass" for n in range(1, 7)}
    return {
        "policy_version": "1",
        "hook_event": "PreToolUse",
        "timestamp": "2026-05-31T00:00:00Z",
        "session_id": "s",
        "workspace_root": "/w",
        "transcript_path": None,
        "actor": {
            "active_agent": "ARTHUR",
            "active_role": "orchestrator",
            "subagent_id": None,
        },
        "tool_attempt": {
            "tool_name": "read_file",
            "tool_use_id": "tu",
            "tool_input": {"a": 1},
            "tool_response": None,
        },
        "workflow": {
            "workflow_id": "w",
            "turn_id": "t",
            "state_before": "ST-001",
            "selected_path": None,
            "explicit_path": None,
            "doc_type": None,
            "open_question_count": 0,
            "user_choice": None,
            "approval_prompted": None,
        },
        "blackboard": {
            "row_present": True,
            "row_schema_valid": True,
            "row_id": "BBR-000001",
            "lifecycle_stage": "intake",
            "fsm_state_ref": "ST-001",
            "required_gates_passed": True,
            "gates": gates,
        },
    }


def test_snapshot_round_trip_and_field_access() -> None:
    data = _snapshot_dict()
    snap = Snapshot.from_dict(data)
    assert snap.to_dict() == data
    assert snap.session_id == "s"
    assert isinstance(snap.tool_calls, ToolCalls)
    assert snap.tool_calls.runSubagent == 0
    assert isinstance(snap.presend, Presend)
    assert snap.presend.result == "pass"
    assert snap.presend.failed_check is None


def test_blackboard_round_trip_and_field_access() -> None:
    data = _blackboard_dict()
    row = BlackboardRow.from_dict(data)
    assert row.to_dict() == data
    assert row.row_id == "BBR-000001"
    assert isinstance(row.owner_lock, OwnerLock)
    assert row.owner_lock.active is None
    assert isinstance(row.terminal, Terminal)
    assert row.terminal.is_terminal is False
    assert isinstance(row.audit, Audit)
    assert row.audit.created_by == "ARTHUR"
    assert row.gates["BG-001"] == "pass"


def test_envelope_round_trip_and_field_access() -> None:
    data = _envelope_dict()
    env = Envelope.from_dict(data)
    assert env.to_dict() == data
    assert env.hook_event == "PreToolUse"
    assert isinstance(env.actor, Actor)
    assert env.actor.active_agent == "ARTHUR"
    assert isinstance(env.tool_attempt, ToolAttempt)
    assert env.tool_attempt.tool_name == "read_file"
    assert isinstance(env.workflow, WorkflowContext)
    assert env.workflow.workflow_id == "w"
    assert isinstance(env.blackboard, BlackboardContext)
    assert env.blackboard.gates["BG-001"] == "pass"


def test_decision_round_trip_required_only() -> None:
    data = {"decision": "allow", "reason_id": "CHK-001", "reason": "ok"}
    dec = Decision.from_dict(data)
    assert dec.to_dict() == data
    assert dec.decision == "allow"
    assert dec.state_after is None
    assert dec.suppressed_action_ids is None
    assert dec.additional_context is None
    assert dec.updated_input is None
    assert dec.continue_ is None


def test_decision_round_trip_all_optional_fields() -> None:
    data = {
        "decision": "deny",
        "reason_id": "INV-021",
        "reason": "blocked",
        "state_after": "ST-900",
        "suppressed_action_ids": ["AC-001", "AC-002"],
        "additional_context": "ctx",
        "updated_input": {"k": "v"},
        "continue": False,
    }
    dec = Decision.from_dict(data)
    assert dec.to_dict() == data
    assert dec.state_after == "ST-900"
    assert dec.suppressed_action_ids == ["AC-001", "AC-002"]
    assert dec.additional_context == "ctx"
    assert dec.updated_input == {"k": "v"}
    assert dec.continue_ is False
