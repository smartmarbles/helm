"""Profile #4 blackboard gates (spec015 Phase 6).

Pure-functional, deterministic evaluators over the per-turn snapshot and the
blackboard row:

* :mod:`helm_controller.gates.stage_state_map` — the POL-053 lifecycle-stage /
  FSM-state / owner-role consistency table (consumed by BG-002 and INV-021).
* :mod:`helm_controller.gates.bg_rules` / :mod:`helm_controller.gates.bg_evaluator`
  — the BG-001..BG-006 hard quality gates (POL-054, ascending fail-fast).
* :mod:`helm_controller.gates.presend_checks` — the CHK-001..CHK-014 pre-send
  compliance gate (POL-020/POL-021, ascending fail-fast).

These modules compute results from their inputs; they never mutate the store.
"""

from __future__ import annotations
