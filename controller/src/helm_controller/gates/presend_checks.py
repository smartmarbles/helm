"""CHK-001..CHK-014 hard pre-send compliance gate — POL-019..POL-024
(spec015 Task 6.4).

Transcribed faithfully from the normative source
``artifacts/docs/orchestration-fsm-policy-and-test-matrix.md`` §5. Checks are
evaluated in strict ascending CHK order (POL-020) and stop on the first failure
(POL-021, fail-fast). On the first failed check the result carries
``presend.result = fail``, ``presend.failed_check = CHK-###`` and the canonical
deny routing to ST-903 (POL-022).

CHK-003 (action-matrix legality) is NOT reimplemented here — it reuses the
Phase 5 :func:`~helm_controller.fsm.action_matrix.check_action_matrix`.

Pure functional: computed from ``snapshot``; the store is never mutated.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from types import MappingProxyType

from helm_controller.contracts.decision import Decision
from helm_controller.contracts.snapshot import Snapshot
from helm_controller.fsm.action_matrix import check_action_matrix
from helm_controller.fsm.actions import action_by_id
from helm_controller.fsm.states import State, state_by_id

CHK_003 = "CHK-003"
PRE_SEND_BLOCKED_STATE = State.PRE_SEND_BLOCKED.value

CHK_ORDER: tuple[str, ...] = tuple(f"CHK-{n:03d}" for n in range(1, 15))

DISPATCH_ACTION = "AC-002"
CLARIFIER_ACTION = "AC-004"
APPROVAL_ACTION = "AC-005"
EXECUTE_ACTION = "AC-006"
PROCESS_AUDIT_ACTION = "AC-007"
STOP_ACTIONS = ["AC-008", "AC-011"]
REQUIRED_DISPATCH_KEYS = frozenset(
    {"objective", "constraints", "inputs", "expected_output"}
)
GATE_DOCS = frozenset({"spec", "plan"})
TERMINAL_STATE_IDS = frozenset({"ST-900", "ST-901", "ST-902"})


def chk_001(s: Snapshot) -> bool:
    return any(
        (
            s.pending_interrupt != "stop",
            all((s.actions == STOP_ACTIONS, s.state_after == "ST-901")),
        )
    )


def chk_002(s: Snapshot) -> bool:
    return any(
        (
            s.pending_interrupt != "process_audit",
            all(
                (
                    PROCESS_AUDIT_ACTION in s.actions,
                    DISPATCH_ACTION not in s.actions,
                    EXECUTE_ACTION not in s.actions,
                    s.state_after == "ST-090",
                )
            ),
        )
    )


def chk_004(s: Snapshot) -> bool:
    return any(
        (
            s.outbound_sender != "orchestrator",
            s.outbound_message_type != "deliverable_content",
        )
    )


def chk_005(s: Snapshot) -> bool:
    return any(
        (
            s.owner_before != "clarifier",
            not all(
                (
                    s.outbound_sender == "orchestrator",
                    s.outbound_message_type == "question_prompt",
                )
            ),
        )
    )


def chk_006(s: Snapshot) -> bool:
    return any(
        (s.open_question_count == 0, s.prompt_options == ["quiz", "inline", "defer"])
    )


def chk_007(s: Snapshot) -> bool:
    return any(
        (
            s.open_question_count == 0,
            s.user_choice in {"quiz", "inline"},
            CLARIFIER_ACTION not in s.actions,
        )
    )


def chk_008(s: Snapshot) -> bool:
    return any(
        (
            s.doc_type not in GATE_DOCS,
            s.open_question_count == 0,
            s.open_question_protocol_resolved is True,
            APPROVAL_ACTION not in s.actions,
        )
    )


def chk_009(s: Snapshot) -> bool:
    return any(
        (
            s.state_before != "ST-070",
            s.phase_execution_started is False,
            s.event == "EV-015",
        )
    )


def chk_010(s: Snapshot) -> bool:
    return any((s.explicit_path is None, s.selected_path == s.explicit_path))


def chk_011(s: Snapshot) -> bool:
    return any(
        (
            DISPATCH_ACTION not in s.actions,
            REQUIRED_DISPATCH_KEYS <= set(s.dispatch_payload_keys),
        )
    )


def chk_012(s: Snapshot) -> bool:
    return any((s.delegation_claimed is False, s.tool_calls.runSubagent >= 1))


def chk_013(s: Snapshot) -> bool:
    return any(
        (len(s.output_paths) <= 1, len(set(s.output_paths)) == len(s.output_paths))
    )


def chk_014(s: Snapshot) -> bool:
    return any((s.state_before not in TERMINAL_STATE_IDS, s.event == "EV-001"))


def chk_003(s: Snapshot) -> bool:
    """CHK-003: every matrix-governed action is allowed in ``state_before``.

    Delegates to the Phase 5 action-matrix check (reused, not reimplemented).
    """
    state = state_by_id(s.state_before)
    actions = [action_by_id(action_id) for action_id in s.actions]
    return check_action_matrix(state, actions, s).passed


_Predicate = Callable[[Snapshot], bool]

PREDICATES: "MappingProxyType[str, _Predicate]" = MappingProxyType(
    {
        "CHK-001": chk_001,
        "CHK-002": chk_002,
        "CHK-003": chk_003,
        "CHK-004": chk_004,
        "CHK-005": chk_005,
        "CHK-006": chk_006,
        "CHK-007": chk_007,
        "CHK-008": chk_008,
        "CHK-009": chk_009,
        "CHK-010": chk_010,
        "CHK-011": chk_011,
        "CHK-012": chk_012,
        "CHK-013": chk_013,
        "CHK-014": chk_014,
    }
)

REASON: "MappingProxyType[str, str]" = MappingProxyType(
    {
        "CHK-001": "stop interrupt without ST-901 + [AC-008, AC-011]",
        "CHK-002": "process-audit interrupt with dispatch/execute or wrong state",
        "CHK-003": "action forbidden in state_before (matrix legality)",
        "CHK-004": "orchestrator emitting deliverable_content",
        "CHK-005": "clarifier owner but orchestrator sent question_prompt",
        "CHK-006": "open questions but prompt_options not [quiz, inline, defer]",
        "CHK-007": "clarifier invoked without a quiz/inline user choice",
        "CHK-008": "gate doc approval prompted with unresolved open questions",
        "CHK-009": "phase execution started in ST-070 without approve (EV-015)",
        "CHK-010": "selected_path diverges from explicit_path",
        "CHK-011": "dispatch missing required brief keys",
        "CHK-012": "delegation claimed without a runSubagent call",
        "CHK-013": "duplicate output paths in a parallel batch",
        "CHK-014": "non-EV-001 event from a terminal state",
    }
)


@dataclass(frozen=True)
class PresendResult:
    """Outcome of the pre-send gate (POL-022)."""

    passed: bool
    result: str
    failed_check: str | None
    decision: Decision | None


def run_presend_checks(snapshot: Snapshot) -> PresendResult:
    """Evaluate CHK-001..CHK-014 ascending with fail-fast (POL-020/POL-021)."""
    for chk_id in CHK_ORDER:
        if not PREDICATES[chk_id](snapshot):
            decision = Decision(
                decision="deny",
                reason_id=chk_id,
                reason=f"{chk_id}: {REASON[chk_id]}",
                state_after=PRE_SEND_BLOCKED_STATE,
            )
            return PresendResult(
                passed=False,
                result="fail",
                failed_check=chk_id,
                decision=decision,
            )
    return PresendResult(passed=True, result="pass", failed_check=None, decision=None)
