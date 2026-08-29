"""Shared snapshot / blackboard factories for the Phase 6 unit tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from helm_controller.contracts.blackboard import (
    Audit,
    BlackboardRow,
    OwnerLock,
    Terminal,
)
from helm_controller.contracts.snapshot import Presend, Snapshot, ToolCalls
from helm_controller.gates.bg_rules import BG_ORDER

_FUTURE = "2026-12-31T00:00:00Z"


@pytest.fixture
def snapshot_factory() -> Callable[..., Snapshot]:
    def _make(**overrides: Any) -> Snapshot:
        base: dict[str, Any] = dict(
            session_id="s",
            workflow_id="w",
            session_active_workflow_id=None,
            predecessor_workflow_id=None,
            successor_workflow_id=None,
            workflow_lifecycle_before="non_terminal_active",
            workflow_lifecycle_after="non_terminal_active",
            turn_id="t",
            state_before="ST-010",
            state_after="ST-020",
            prior_non_terminal_fsm_state=None,
            owner_before="orchestrator",
            owner_after="orchestrator",
            event="EV-004",
            boundary_event=None,
            selected_path=None,
            explicit_path=None,
            doc_type=None,
            open_question_count=0,
            pending_interrupt="none",
            actions=[],
            outbound_sender="orchestrator",
            outbound_message_type="status",
            prompt_options=[],
            user_choice=None,
            approval_prompted=False,
            open_question_protocol_resolved=False,
            delegation_claimed=False,
            dispatch_payload_keys=[],
            phase_execution_started=False,
            suppressed_action_ids=[],
            tool_calls=ToolCalls(runSubagent=0),
            presend=Presend(executed=True, result="pass", failed_check=None),
            output_paths=[],
        )
        base.update(overrides)
        return Snapshot(**base)

    return _make


@pytest.fixture
def blackboard_factory() -> Callable[..., BlackboardRow]:
    def _make(**overrides: Any) -> BlackboardRow:
        lock_overrides = overrides.pop("owner_lock", {})
        terminal_overrides = overrides.pop("terminal", {})
        audit_overrides = overrides.pop("audit", {})
        lock = dict(
            active="ARTHUR",
            lock_token="tok",
            acquired_at="2026-05-31T11:00:00Z",
            expires_at=_FUTURE,
            is_stale=False,
            active_lock_count=1,
        )
        lock.update(lock_overrides)
        terminal = dict(
            is_terminal=False,
            terminal_state=None,
            terminalized_at=None,
            terminal_reason=None,
        )
        terminal.update(terminal_overrides)
        audit = dict(
            created_at="2026-05-31T10:00:00Z",
            created_by="ARTHUR",
            revision=1,
            immutable_fields_hash="h",
            audit_fields_mutated=False,
        )
        audit.update(audit_overrides)
        base: dict[str, Any] = dict(
            row_present=True,
            row_schema_valid=True,
            row_id="BBR-000001",
            session_id="s",
            workflow_id="w",
            predecessor_workflow_id=None,
            successor_workflow_id=None,
            item_id="item",
            lifecycle_stage="route",
            workflow_lifecycle="non_terminal_active",
            fsm_state_ref="ST-010",
            prior_non_terminal_fsm_state=None,
            owner_lock=OwnerLock(**lock),
            gates={g: "pass" for g in BG_ORDER},
            required_gates_passed=True,
            terminal=Terminal(**terminal),
            audit=Audit(**audit),
            mutation_attempt_keys=[],
        )
        base.update(overrides)
        return BlackboardRow(**base)

    return _make
