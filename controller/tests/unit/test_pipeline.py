"""Tests for the decision pipeline orchestrator (spec015 Task 8.1 / 8.5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from helm_controller.fsm.events import event_by_id
from helm_controller.hooks.agent_stack import AgentStackStore
from helm_controller.hooks.envelope_assembler import EnvelopeAssembler
from helm_controller.hooks.pipeline import (
    BOUNDARY_ILLEGAL_REASON_ID,
    DecisionPipeline,
    PipelineRequest,
)
from helm_controller.store.adapter import RuntimeStoreAdapter
from helm_controller.store.identity import RuntimeIdentity

_SESSION = "sess-1"
_WF = "wf-1"


class _FakeBoundaryDecision:
    def __init__(self, legal: bool, reason: str = "boundary detail") -> None:
        self.legal = legal
        self.reason = reason


class _FakeLifecycle:
    def __init__(self, legal: bool) -> None:
        self._decision = _FakeBoundaryDecision(legal)
        self.calls = 0

    def evaluate(self, _request: object) -> _FakeBoundaryDecision:
        self.calls += 1
        return self._decision


def _payload(event: str, **extra: object) -> dict:
    base: dict = {
        "hookEventName": event,
        "sessionId": _SESSION,
        "transcript_path": "/tmp/t.jsonl",
        "timestamp": "2026-05-31T12:00:00Z",
    }
    base.update(extra)
    return base


def _pipeline(
    tmp_path: Path, *, role: str = "implementer", lifecycle: object | None = None
):
    store = RuntimeStoreAdapter(tmp_path / "store.db")
    stack = AgentStackStore(tmp_path / "store.db")
    assembler = EnvelopeAssembler(
        store, stack, tmp_path, role_resolver=lambda _name: role
    )
    pipeline = DecisionPipeline(assembler, lifecycle_evaluator=lifecycle)
    return store, stack, pipeline


def _seed(store: RuntimeStoreAdapter, stack: AgentStackStore) -> None:
    store.create(
        RuntimeIdentity(_SESSION, _WF, "0"),
        row_id="BBR-000001",
        item_id="item-1",
        fsm_state_ref="ST-000",
        created_by="ARTHUR",
        immutable_fields_hash="h",
    )
    stack.set_active_workflow(_SESSION, _WF)


# --------------------------------------------------------------------------- #
# parse / assemble short-circuits
# --------------------------------------------------------------------------- #
def test_non_dict_payload_parse_failure_denies(tmp_path: Path) -> None:
    _store, _stack, pipeline = _pipeline(tmp_path)
    result = pipeline.evaluate(PipelineRequest(payload=["not", "a", "dict"]))
    assert result.hook_event == ""
    assert result.decision.decision == "deny"
    assert result.decision.reason_id == "PC-004"


def test_dict_payload_missing_event_parse_failure(tmp_path: Path) -> None:
    _store, _stack, pipeline = _pipeline(tmp_path)
    result = pipeline.evaluate(PipelineRequest(payload={"sessionId": _SESSION}))
    assert result.decision.decision == "deny"
    assert result.hook_event == ""


def test_parse_failure_recovers_known_event_name(tmp_path: Path) -> None:
    _store, _stack, pipeline = _pipeline(tmp_path)
    # Recognized event name but missing sessionId -> parse failure with event echoed.
    result = pipeline.evaluate(
        PipelineRequest(payload={"hookEventName": "PreToolUse"})
    )
    assert result.decision.decision == "deny"
    assert result.hook_event == "PreToolUse"


def test_assembly_pc004_short_circuits(tmp_path: Path) -> None:
    _store, _stack, pipeline = _pipeline(tmp_path)
    result = pipeline.evaluate(
        PipelineRequest(
            payload=_payload("PreToolUse", tool_name="read_file", tool_use_id="tu-1")
        )
    )
    assert result.decision.decision == "deny"
    assert result.decision.reason_id == "PC-004"


# --------------------------------------------------------------------------- #
# lifecycle boundary stage
# --------------------------------------------------------------------------- #
def test_illegal_boundary_denies_chk003(tmp_path: Path) -> None:
    store, stack, pipeline = _pipeline(tmp_path, lifecycle=_FakeLifecycle(legal=False))
    _seed(store, stack)
    result = pipeline.evaluate(
        PipelineRequest(
            payload=_payload("Stop", stop_hook_active=False),
            boundary_request=object(),
        )
    )
    assert result.decision.decision == "deny"
    assert result.decision.reason_id == BOUNDARY_ILLEGAL_REASON_ID
    assert result.decision.state_after == "ST-903"


def test_legal_boundary_continues_to_allow(tmp_path: Path) -> None:
    lifecycle = _FakeLifecycle(legal=True)
    store, stack, pipeline = _pipeline(tmp_path, lifecycle=lifecycle)
    _seed(store, stack)
    result = pipeline.evaluate(
        PipelineRequest(
            payload=_payload("Stop", stop_hook_active=False),
            boundary_request=object(),
        )
    )
    assert lifecycle.calls == 1
    assert result.decision.decision == "allow"


def test_boundary_request_without_evaluator_is_skipped(tmp_path: Path) -> None:
    store, stack, pipeline = _pipeline(tmp_path, lifecycle=None)
    _seed(store, stack)
    result = pipeline.evaluate(
        PipelineRequest(
            payload=_payload("Stop", stop_hook_active=False),
            boundary_request=object(),
        )
    )
    assert result.decision.decision == "allow"


# --------------------------------------------------------------------------- #
# role-tool matrix + conditional checks stage
# --------------------------------------------------------------------------- #
def test_matrix_deny_pc001(tmp_path: Path) -> None:
    store, stack, pipeline = _pipeline(tmp_path, role="orchestrator")
    _seed(store, stack)
    result = pipeline.evaluate(
        PipelineRequest(
            payload=_payload(
                "PreToolUse", tool_name="run_in_terminal", tool_use_id="tu-1"
            )
        )
    )
    assert result.decision.decision == "deny"
    assert result.decision.reason_id == "PC-001"


def test_conditional_check_fail_pc003(tmp_path: Path) -> None:
    store, stack, pipeline = _pipeline(tmp_path, role="implementer")
    _seed(store, stack)
    scr_path = str(tmp_path / ".scr" / "x.py")
    result = pipeline.evaluate(
        PipelineRequest(
            payload=_payload(
                "PreToolUse",
                tool_name="create_file",
                tool_input={"filePath": scr_path},
                tool_use_id="tu-1",
            )
        )
    )
    assert result.decision.decision == "deny"
    assert result.decision.reason_id == "PC-003"


def test_conditional_check_pass_allows(tmp_path: Path) -> None:
    store, stack, pipeline = _pipeline(tmp_path, role="implementer")
    _seed(store, stack)
    ok_path = str(tmp_path / "pkg" / "x.py")
    result = pipeline.evaluate(
        PipelineRequest(
            payload=_payload(
                "PreToolUse",
                tool_name="create_file",
                tool_input={"filePath": ok_path},
                tool_use_id="tu-1",
            )
        )
    )
    assert result.decision.decision == "allow"


def test_matrix_direct_allow_read_tool(tmp_path: Path) -> None:
    # implementer + read class -> ALLOW directly (no conditional checks).
    store, stack, pipeline = _pipeline(tmp_path, role="implementer")
    _seed(store, stack)
    result = pipeline.evaluate(
        PipelineRequest(
            payload=_payload("PreToolUse", tool_name="read_file", tool_use_id="tu-1")
        )
    )
    assert result.decision.decision == "allow"


# --------------------------------------------------------------------------- #
# FSM / gate / invariant / presend stages
# --------------------------------------------------------------------------- #
def test_fsm_legal_transition_allows(tmp_path: Path, snapshot_factory) -> None:
    store, stack, pipeline = _pipeline(tmp_path)
    _seed(store, stack)
    snapshot = snapshot_factory(state_before="ST-000", event="EV-001")
    result = pipeline.evaluate(
        PipelineRequest(
            payload=_payload("Stop", stop_hook_active=False),
            snapshot=snapshot,
            event=event_by_id("EV-001"),
        )
    )
    assert result.decision.decision == "allow"


def test_fsm_illegal_transition_denies(tmp_path: Path, snapshot_factory) -> None:
    store, stack, pipeline = _pipeline(tmp_path)
    _seed(store, stack)
    snapshot = snapshot_factory(state_before="ST-010", event="EV-019")
    result = pipeline.evaluate(
        PipelineRequest(
            payload=_payload("Stop", stop_hook_active=False),
            snapshot=snapshot,
            event=event_by_id("EV-019"),
        )
    )
    assert result.decision.decision == "deny"
    assert result.decision.reason_id == "CHK-003"
    assert "illegal FSM transition" in result.decision.reason


def test_all_gates_pass_allow(
    tmp_path: Path, snapshot_factory, blackboard_factory
) -> None:
    store, stack, pipeline = _pipeline(tmp_path)
    _seed(store, stack)
    result = pipeline.evaluate(
        PipelineRequest(
            payload=_payload("Stop", stop_hook_active=False),
            snapshot=snapshot_factory(),
            blackboard=blackboard_factory(),
        )
    )
    assert result.decision.decision == "allow"
    assert result.decision.reason_id == ""


def test_bg_gate_fail_denies(
    tmp_path: Path, snapshot_factory, blackboard_factory
) -> None:
    store, stack, pipeline = _pipeline(tmp_path)
    _seed(store, stack)
    blackboard = blackboard_factory(
        row_present=False, gates={}, required_gates_passed=False
    )
    result = pipeline.evaluate(
        PipelineRequest(
            payload=_payload("Stop", stop_hook_active=False),
            snapshot=snapshot_factory(),
            blackboard=blackboard,
        )
    )
    assert result.decision.decision == "deny"
    assert result.decision.reason_id.startswith("BG-")


def test_invariant_fail_denies(
    tmp_path: Path, snapshot_factory, blackboard_factory
) -> None:
    store, stack, pipeline = _pipeline(tmp_path)
    _seed(store, stack)
    snapshot = snapshot_factory(
        outbound_sender="orchestrator",
        outbound_message_type="deliverable_content",
    )
    result = pipeline.evaluate(
        PipelineRequest(
            payload=_payload("Stop", stop_hook_active=False),
            snapshot=snapshot,
            blackboard=blackboard_factory(),
        )
    )
    assert result.decision.decision == "deny"
    assert result.decision.reason_id == "INV-001"


def test_presend_check_fail_denies(tmp_path: Path, snapshot_factory) -> None:
    store, stack, pipeline = _pipeline(tmp_path)
    _seed(store, stack)
    snapshot = snapshot_factory(selected_path="full", explicit_path="standard")
    result = pipeline.evaluate(
        PipelineRequest(
            payload=_payload("Stop", stop_hook_active=False),
            snapshot=snapshot,
        )
    )
    assert result.decision.decision == "deny"
    assert result.decision.reason_id.startswith("CHK-")


# --------------------------------------------------------------------------- #
# final decision: ask vs allow
# --------------------------------------------------------------------------- #
def test_missing_checkpoint_asks(tmp_path: Path) -> None:
    store, stack, pipeline = _pipeline(tmp_path)
    _seed(store, stack)
    result = pipeline.evaluate(
        PipelineRequest(
            payload=_payload("Stop", stop_hook_active=False),
            checkpoint_required=True,
        )
    )
    assert result.decision.decision == "ask"
    assert result.decision.reason_id == "PC-006"


def test_clean_pipeline_allows(tmp_path: Path) -> None:
    store, stack, pipeline = _pipeline(tmp_path)
    _seed(store, stack)
    result = pipeline.evaluate(
        PipelineRequest(payload=_payload("Stop", stop_hook_active=False))
    )
    assert result.decision.decision == "allow"
