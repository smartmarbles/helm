"""Residual parity checks for Stop / SubagentStop boundaries (spec015 Task 8.4).

Some violations occur in model prose BEFORE any disallowed tool call is attempted
(an orchestrator that writes a deliverable directly, or claims to have delegated
without ever calling ``runSubagent``). ``PreToolUse`` cannot catch these because
no tool invocation exists yet. The ``Stop`` and ``SubagentStop`` hooks run a
best-effort residual scan of the turn transcript (boundary contract §7.1) and,
on a detected violation, deny via the event-native top-level
``{"decision": "block", ...}`` shape with a corrective ``additionalContext``
reroute. Per §7.2/§7.3 this is best-effort real-time mitigation only; LENS plus
the PROBE regression suites remain the authoritative post-hoc truth layer.
"""
