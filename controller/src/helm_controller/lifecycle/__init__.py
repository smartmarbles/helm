"""Lifecycle boundary evaluator package (spec015 Phase 7).

The authoritative, un-bypassable entry point for all workflow lifecycle
boundary events — ``new`` / ``supersede`` / ``suspend`` / ``resume`` /
``terminalize`` (spec §3.3, §4). The package layers three concerns:

* :mod:`helm_controller.lifecycle.legality` — the source-lifecycle x
  boundary-event legality matrix (spec §4.4) and the required state mutations.
* :mod:`helm_controller.lifecycle.evaluator` — the entry point that resolves the
  source lifecycle, applies the legal mutation through the runtime-store write
  path, or denies (incl. the ST-000 disambiguation of spec §4.5).
* :mod:`helm_controller.lifecycle.prior_state` — ``prior_non_terminal_fsm_state``
  write/clear wiring per POL-014C.
* :mod:`helm_controller.lifecycle.terminalize` — ``boundary_event = terminalize``
  enforcement on every terminal FSM transition per POL-014B.
"""
