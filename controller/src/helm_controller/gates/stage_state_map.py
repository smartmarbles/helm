"""Lifecycle-stage / FSM-state / owner-role consistency table — POL-053
(spec015 Task 6.2).

Transcribed faithfully from the normative source
``artifacts/docs/orchestration-fsm-policy-and-test-matrix.md`` §11.2 ("Lifecycle
stage and ownership requirements") and POL-053. This table is consumed by two
enforcement layers:

* **BG-002** reads :func:`allowed_states` — its pass predicate requires
  ``stage_state_map[lifecycle_stage]`` to contain ``state_before``.
* **INV-021** reads :func:`registry_role` — the audit field
  ``owner_lock.active`` is an agent NAME (e.g. ``ARTHUR``), but enforcement
  evaluates by ROLE. ``registry_role`` resolves the name to its policy role;
  ``null`` (no lock held) resolves to ``None``.

:func:`check_consistency` is the full POL-053 validator (all three columns). It
is exercised directly by ``test_stage_state_map.py`` because the BG/INV layers
only traverse the consistent-triple path — the inconsistency branches and the
unknown-key fallbacks require direct invocation for full branch coverage.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from helm_controller.fsm.states import State


@dataclass(frozen=True)
class StageRule:
    """Allowed FSM states and owner roles for one lifecycle stage (POL-053)."""

    allowed_states: frozenset[str]
    allowed_roles: frozenset[str | None]


# POL-053 §11.2 table. ``None`` in ``allowed_roles`` means the stage requires no
# owner lock (the ``null`` rows: suspended, terminal).
STAGE_STATE_MAP: "MappingProxyType[str, StageRule]" = MappingProxyType(
    {
        "intake": StageRule(frozenset({"ST-000"}), frozenset({"orchestrator"})),
        "route": StageRule(frozenset({"ST-010"}), frozenset({"orchestrator"})),
        "prepare_dispatch": StageRule(
            frozenset({"ST-020", "ST-903"}), frozenset({"orchestrator"})
        ),
        "dispatch": StageRule(frozenset({"ST-030"}), frozenset({"orchestrator"})),
        "await_result": StageRule(
            frozenset({"ST-040", "ST-050"}),
            frozenset({"orchestrator", "clarifier"}),
        ),
        "approval": StageRule(
            frozenset({"ST-060", "ST-070"}), frozenset({"orchestrator"})
        ),
        "execution": StageRule(frozenset({"ST-080"}), frozenset({"orchestrator"})),
        "suspended": StageRule(frozenset({"ST-000"}), frozenset({None})),
        "terminal": StageRule(
            frozenset({"ST-900", "ST-901", "ST-902"}), frozenset({None})
        ),
    }
)

_KNOWN_STATE_IDS: frozenset[str] = frozenset(state.value for state in State)


class Consistency(Enum):
    """Outcome of a POL-053 (stage, state, role) consistency evaluation."""

    CONSISTENT = "consistent"
    UNKNOWN_STAGE = "unknown_stage"
    UNKNOWN_STATE = "unknown_state"
    INCONSISTENT_STATE = "inconsistent_state"
    INCONSISTENT_ROLE = "inconsistent_role"


def allowed_states(lifecycle_stage: str) -> frozenset[str] | None:
    """Return the FSM states permitted for ``lifecycle_stage`` (BG-002 input).

    Returns ``None`` when ``lifecycle_stage`` is not a known POL-053 stage.
    """
    rule = STAGE_STATE_MAP.get(lifecycle_stage)
    return rule.allowed_states if rule is not None else None


def registry_role(
    agent_name: str | None, resolve_role: Callable[[str], str]
) -> str | None:
    """Resolve an ``owner_lock.active`` agent NAME to its policy ROLE (INV-021).

    ``agent_name is None`` (no lock held) resolves to ``None``. A registered
    name resolves through ``resolve_role``; an unregistered name resolves to
    whatever ``resolve_role`` returns for it (``UNKNOWN`` for the standard
    :class:`~helm_controller.policy.registry.AgentRoleRegistry`).
    """
    if agent_name is None:
        return None
    return resolve_role(agent_name)


def check_consistency(
    lifecycle_stage: str, fsm_state: str, owner_role: str | None
) -> Consistency:
    """Evaluate the full POL-053 (stage, state, role) triple.

    Branches, in order: unknown stage, unknown FSM-state id, state not allowed
    for the stage, owner role not allowed for the stage, otherwise consistent.
    """
    rule = STAGE_STATE_MAP.get(lifecycle_stage)
    if rule is None:
        return Consistency.UNKNOWN_STAGE
    if fsm_state not in _KNOWN_STATE_IDS:
        return Consistency.UNKNOWN_STATE
    if fsm_state not in rule.allowed_states:
        return Consistency.INCONSISTENT_STATE
    if owner_role not in rule.allowed_roles:
        return Consistency.INCONSISTENT_ROLE
    return Consistency.CONSISTENT
