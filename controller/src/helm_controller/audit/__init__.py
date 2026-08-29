"""Audit plane for the decision pipeline (spec015 Task 8.3).

Two cooperating concerns live here:

* :mod:`helm_controller.audit.telemetry` — best-effort observability signals that
  MUST NEVER break policy enforcement when a sink fails.
* :mod:`helm_controller.audit.split_plane` — turn-level recording of the case
  where the Python controller allowed an action but VS Code natively rejected it
  (e.g. the user clicked deny on a permission prompt). The FSM MUST NOT advance
  on a native rejection, so this is recorded out-of-band from the FSM.
"""
