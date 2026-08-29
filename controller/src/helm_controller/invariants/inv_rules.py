"""INV-001..INV-021 invariant predicates — §8 + INV-021 (spec015 Task 6.3).

Transcribed faithfully from the normative source
``artifacts/docs/orchestration-fsm-policy-and-test-matrix.md`` §8 ("Machine-
Checkable Invariants"). Each predicate returns ``True`` when the invariant holds.
Boolean OR/AND structure is expressed with :func:`any` / :func:`all` over the
literal conjuncts so the transcription tracks the source predicates clause for
clause. INV-021 consumes :func:`~helm_controller.gates.stage_state_map.registry_role`
— ``owner_lock.active`` is an agent NAME; enforcement evaluates the resolved ROLE.
"""

from __future__ import annotations

from collections.abc import Callable
from types import MappingProxyType

from helm_controller.contracts.blackboard import BlackboardRow
from helm_controller.contracts.snapshot import Snapshot
from helm_controller.gates.stage_state_map import registry_role

INV_ORDER: tuple[str, ...] = tuple(f"INV-{n:03d}" for n in range(1, 22))

DISPATCH_ACTION = "AC-002"
CLARIFIER_ACTION = "AC-004"
APPROVAL_ACTION = "AC-005"
EXECUTE_ACTION = "AC-006"
STOP_ACTIONS = ["AC-008", "AC-011"]
REQUIRED_DISPATCH_KEYS = frozenset(
    {"objective", "constraints", "inputs", "expected_output"}
)
GATE_DOCS = frozenset({"spec", "plan"})
TERMINAL_STATE_IDS = frozenset({"ST-900", "ST-901", "ST-902"})
_ResolveRole = Callable[[str], str]


def inv_001(s: Snapshot, b: BlackboardRow, r: _ResolveRole) -> bool:
    return any(
        (
            s.outbound_sender != "orchestrator",
            s.outbound_message_type != "deliverable_content",
        )
    )


def inv_002(s: Snapshot, b: BlackboardRow, r: _ResolveRole) -> bool:
    return any((s.delegation_claimed is False, s.tool_calls.runSubagent >= 1))


def inv_003(s: Snapshot, b: BlackboardRow, r: _ResolveRole) -> bool:
    return any((s.explicit_path is None, s.selected_path == s.explicit_path))


def inv_004(s: Snapshot, b: BlackboardRow, r: _ResolveRole) -> bool:
    return any(
        (s.open_question_count == 0, s.prompt_options == ["quiz", "inline", "defer"])
    )


def inv_005(s: Snapshot, b: BlackboardRow, r: _ResolveRole) -> bool:
    return any(
        (
            s.open_question_count == 0,
            s.user_choice in {"quiz", "inline"},
            CLARIFIER_ACTION not in s.actions,
        )
    )


def inv_006(s: Snapshot, b: BlackboardRow, r: _ResolveRole) -> bool:
    return any(
        (
            s.doc_type != "spec",
            s.open_question_count == 0,
            s.open_question_protocol_resolved is True,
            APPROVAL_ACTION not in s.actions,
        )
    )


def inv_007(s: Snapshot, b: BlackboardRow, r: _ResolveRole) -> bool:
    return any(
        (
            s.doc_type != "plan",
            s.open_question_count == 0,
            s.open_question_protocol_resolved is True,
            APPROVAL_ACTION not in s.actions,
        )
    )


def inv_008(s: Snapshot, b: BlackboardRow, r: _ResolveRole) -> bool:
    return any(
        (
            s.state_before != "ST-070",
            s.event == "EV-015",
            s.phase_execution_started is False,
        )
    )


def inv_009(s: Snapshot, b: BlackboardRow, r: _ResolveRole) -> bool:
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


def inv_010(s: Snapshot, b: BlackboardRow, r: _ResolveRole) -> bool:
    return any(
        (
            s.event != "EV-002",
            all((s.state_after == "ST-901", s.actions == STOP_ACTIONS)),
        )
    )


def inv_011(s: Snapshot, b: BlackboardRow, r: _ResolveRole) -> bool:
    return any(
        (
            s.event != "EV-003",
            all(
                (
                    s.state_after == "ST-090",
                    DISPATCH_ACTION not in s.actions,
                    EXECUTE_ACTION not in s.actions,
                )
            ),
        )
    )


def inv_012(s: Snapshot, b: BlackboardRow, r: _ResolveRole) -> bool:
    return s.presend.executed is True


def inv_013(s: Snapshot, b: BlackboardRow, r: _ResolveRole) -> bool:
    return any(
        (
            DISPATCH_ACTION not in s.actions,
            REQUIRED_DISPATCH_KEYS <= set(s.dispatch_payload_keys),
        )
    )


def inv_014(s: Snapshot, b: BlackboardRow, r: _ResolveRole) -> bool:
    return any(
        (len(s.output_paths) <= 1, len(set(s.output_paths)) == len(s.output_paths))
    )


def inv_015(s: Snapshot, b: BlackboardRow, r: _ResolveRole) -> bool:
    return any((s.state_before not in TERMINAL_STATE_IDS, s.event == "EV-001"))


def inv_016(s: Snapshot, b: BlackboardRow, r: _ResolveRole) -> bool:
    return any(
        (
            not all((s.doc_type == "non_gate", s.user_choice == "defer")),
            s.approval_prompted is False,
        )
    )


def inv_017(s: Snapshot, b: BlackboardRow, r: _ResolveRole) -> bool:
    return any(
        (
            not all((s.doc_type in GATE_DOCS, s.user_choice == "defer")),
            s.approval_prompted is True,
        )
    )


def inv_018(s: Snapshot, b: BlackboardRow, r: _ResolveRole) -> bool:
    return any(
        (
            DISPATCH_ACTION not in s.actions,
            all((b.row_present is True, b.row_schema_valid is True)),
        )
    )


def inv_019(s: Snapshot, b: BlackboardRow, r: _ResolveRole) -> bool:
    return any(
        (
            s.state_after not in {"ST-030", "ST-080"},
            b.required_gates_passed is True,
        )
    )


def inv_020(s: Snapshot, b: BlackboardRow, r: _ResolveRole) -> bool:
    return any(
        (
            b.terminal.is_terminal is False,
            b.audit.audit_fields_mutated is False,
        )
    )


def inv_021(s: Snapshot, b: BlackboardRow, r: _ResolveRole) -> bool:
    lock = b.owner_lock
    role = registry_role(lock.active, r)
    return any(
        (
            b.row_present is False,
            all(
                (
                    b.workflow_lifecycle == "non_terminal_active",
                    lock.active_lock_count == 1,
                    role in {"orchestrator", "clarifier"},
                    lock.is_stale is False,
                )
            ),
            all(
                (
                    b.workflow_lifecycle in {"non_terminal_suspended", "terminal"},
                    lock.active_lock_count == 0,
                    lock.active is None,
                )
            ),
        )
    )


_Predicate = Callable[[Snapshot, BlackboardRow, _ResolveRole], bool]

PREDICATES: "MappingProxyType[str, _Predicate]" = MappingProxyType(
    {
        "INV-001": inv_001,
        "INV-002": inv_002,
        "INV-003": inv_003,
        "INV-004": inv_004,
        "INV-005": inv_005,
        "INV-006": inv_006,
        "INV-007": inv_007,
        "INV-008": inv_008,
        "INV-009": inv_009,
        "INV-010": inv_010,
        "INV-011": inv_011,
        "INV-012": inv_012,
        "INV-013": inv_013,
        "INV-014": inv_014,
        "INV-015": inv_015,
        "INV-016": inv_016,
        "INV-017": inv_017,
        "INV-018": inv_018,
        "INV-019": inv_019,
        "INV-020": inv_020,
        "INV-021": inv_021,
    }
)

REASON: "MappingProxyType[str, str]" = MappingProxyType(
    {
        "INV-001": "orchestrator emitted deliverable_content",
        "INV-002": "delegation claimed without a runSubagent call",
        "INV-003": "selected_path diverges from explicit_path",
        "INV-004": "open questions present but prompt_options not [quiz, inline, defer]",
        "INV-005": "clarifier invoked without a quiz/inline user choice",
        "INV-006": "spec approval prompted with unresolved open questions",
        "INV-007": "plan approval prompted with unresolved open questions",
        "INV-008": "phase execution started in ST-070 without approve (EV-015)",
        "INV-009": "clarifier owner but orchestrator sent question_prompt",
        "INV-010": "stop event without ST-901 + [AC-008, AC-011]",
        "INV-011": "process-audit event with dispatch/execute actions",
        "INV-012": "pre-send gate not executed",
        "INV-013": "dispatch missing required brief keys",
        "INV-014": "duplicate output paths in a parallel batch",
        "INV-015": "non-EV-001 event from a terminal state",
        "INV-016": "non-gate defer raised an approval prompt",
        "INV-017": "gate-doc defer did not raise an approval prompt",
        "INV-018": "dispatch without a valid blackboard row",
        "INV-019": "entered ST-030/ST-080 without required gates passed",
        "INV-020": "audit fields mutated on a terminal row",
        "INV-021": "owner-lock state inconsistent with workflow lifecycle/role",
    }
)
