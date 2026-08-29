"""SCR package (spec015 Phase 11).

Controller-owned write path for durable .scr/ records.  Single-writer
serialization via queue.Queue; atomic file commits via os.replace(); derived
SQLite index for fast lookup with REBUILD for recovery.
"""
