"""Machine-checkable invariants INV-001..INV-021 (spec015 Phase 6).

Pure-functional predicates over the per-turn snapshot and (for INV-018..INV-021)
the blackboard row. POL-045: any false invariant is an immediate policy FAIL for
the turn. INV-021 resolves ``owner_lock.active`` (an agent NAME) to a ROLE via
the agent registry — name-based audit and role-based enforcement coexist.
"""

from __future__ import annotations
