"""Runtime store package (spec015 Phase 2).

Houses the SQLite-backed runtime store: the canonical schema and migrations
(Task 2.1) and the connection-managing adapter plus composite-identity model
(Task 2.2). Locking primitives and the session-memory fallback adapter land in
later Phase 2 tasks.
"""
