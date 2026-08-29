-- Migration 0001 — initial runtime store schema (workflow-scoped persistent tier).
-- spec015 Task 2.1 / spec §5.1 + §5.3.
--
-- This migration builds the same tables as the canonical store/schema.sql.
-- Connection PRAGMAs (journal_mode=WAL, busy_timeout, foreign_keys) are NOT
-- issued here: journal_mode cannot be changed inside a transaction and the
-- pragmas are connection-scoped, not schema DDL. The adapter (Task 2.2) sets
-- them on every connection open before applying migrations.

BEGIN;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT    NOT NULL PRIMARY KEY,
    applied_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS workflows (
    session_id                      TEXT    NOT NULL,
    workflow_id                     TEXT    NOT NULL,

    workflow_lifecycle              TEXT    NOT NULL DEFAULT 'non_terminal_active'
        CHECK (workflow_lifecycle IN (
            'non_terminal_active', 'non_terminal_suspended', 'terminal')),

    fsm_state_ref                   TEXT    NOT NULL
        CHECK (fsm_state_ref GLOB 'ST-[0-9][0-9][0-9]'),
    prior_non_terminal_fsm_state    TEXT
        CHECK (prior_non_terminal_fsm_state IS NULL
               OR prior_non_terminal_fsm_state GLOB 'ST-[0-9][0-9][0-9]'),

    predecessor_workflow_id         TEXT,
    successor_workflow_id           TEXT,

    owner_lock_active               TEXT,
    owner_lock_token                TEXT,
    owner_lock_acquired_at          TEXT,
    owner_lock_expires_at           TEXT,

    revision                        INTEGER NOT NULL DEFAULT 1
        CHECK (revision >= 1),

    boundary_event                  TEXT
        CHECK (boundary_event IS NULL OR boundary_event IN (
            'new', 'supersede', 'suspend', 'resume', 'terminalize')),

    is_terminal                     INTEGER NOT NULL DEFAULT 0
        CHECK (is_terminal IN (0, 1)),
    terminal_state                  TEXT
        CHECK (terminal_state IS NULL
               OR terminal_state IN ('ST-900', 'ST-901', 'ST-902')),
    terminalized_at                 TEXT,
    terminal_reason                 TEXT
        CHECK (terminal_reason IS NULL
               OR terminal_reason IN ('success', 'stop', 'reject', 'superseded')),

    created_at                      TEXT    NOT NULL,
    created_by                      TEXT    NOT NULL,

    PRIMARY KEY (session_id, workflow_id),

    CHECK (predecessor_workflow_id IS NULL
           OR predecessor_workflow_id <> workflow_id),
    CHECK (successor_workflow_id IS NULL
           OR successor_workflow_id <> workflow_id),
    CHECK (workflow_lifecycle = 'non_terminal_active'
           OR owner_lock_active IS NULL),
    CHECK ((is_terminal = 1) = (workflow_lifecycle = 'terminal'))
);

CREATE INDEX IF NOT EXISTS idx_workflows_predecessor
    ON workflows (session_id, predecessor_workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflows_successor
    ON workflows (session_id, successor_workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflows_lifecycle
    ON workflows (session_id, workflow_lifecycle);

CREATE TABLE IF NOT EXISTS blackboard_rows (
    row_id                  TEXT    NOT NULL PRIMARY KEY
        CHECK (row_id GLOB 'BBR-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    session_id              TEXT    NOT NULL,
    workflow_id             TEXT    NOT NULL,
    item_id                 TEXT    NOT NULL,

    lifecycle_stage         TEXT    NOT NULL
        CHECK (lifecycle_stage IN (
            'intake', 'route', 'prepare_dispatch', 'dispatch', 'await_result',
            'approval', 'execution', 'suspended', 'terminal')),

    gate_bg_001             TEXT    NOT NULL DEFAULT 'not_evaluated'
        CHECK (gate_bg_001 IN ('pass', 'fail', 'blocked', 'not_evaluated')),
    gate_bg_002             TEXT    NOT NULL DEFAULT 'not_evaluated'
        CHECK (gate_bg_002 IN ('pass', 'fail', 'blocked', 'not_evaluated')),
    gate_bg_003             TEXT    NOT NULL DEFAULT 'not_evaluated'
        CHECK (gate_bg_003 IN ('pass', 'fail', 'blocked', 'not_evaluated')),
    gate_bg_004             TEXT    NOT NULL DEFAULT 'not_evaluated'
        CHECK (gate_bg_004 IN ('pass', 'fail', 'blocked', 'not_evaluated')),
    gate_bg_005             TEXT    NOT NULL DEFAULT 'not_evaluated'
        CHECK (gate_bg_005 IN ('pass', 'fail', 'blocked', 'not_evaluated')),
    gate_bg_006             TEXT    NOT NULL DEFAULT 'not_evaluated'
        CHECK (gate_bg_006 IN ('pass', 'fail', 'blocked', 'not_evaluated')),

    gate_first_failure_id   TEXT
        CHECK (gate_first_failure_id IS NULL
               OR gate_first_failure_id GLOB 'BG-[0-9][0-9][0-9]'),

    required_gates_passed   INTEGER NOT NULL DEFAULT 0
        CHECK (required_gates_passed IN (0, 1)),

    created_at              TEXT    NOT NULL,
    created_by              TEXT    NOT NULL,
    immutable_fields_hash   TEXT    NOT NULL,
    audit_fields_mutated    INTEGER NOT NULL DEFAULT 0
        CHECK (audit_fields_mutated IN (0, 1)),

    UNIQUE (session_id, workflow_id),
    FOREIGN KEY (session_id, workflow_id)
        REFERENCES workflows (session_id, workflow_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_blackboard_rows_workflow
    ON blackboard_rows (session_id, workflow_id);

CREATE TABLE IF NOT EXISTS mutation_audit (
    audit_id        INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT    NOT NULL,
    workflow_id     TEXT    NOT NULL,
    actor           TEXT    NOT NULL,
    operation       TEXT    NOT NULL,
    operation_id    TEXT,
    from_revision   INTEGER,
    to_revision     INTEGER,
    correlation_id  TEXT,
    recorded_at     TEXT    NOT NULL,
    FOREIGN KEY (session_id, workflow_id)
        REFERENCES workflows (session_id, workflow_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mutation_audit_workflow
    ON mutation_audit (session_id, workflow_id, audit_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mutation_audit_operation_id
    ON mutation_audit (operation_id)
    WHERE operation_id IS NOT NULL;

INSERT OR IGNORE INTO schema_migrations (version, applied_at)
VALUES ('0001_initial', strftime('%Y-%m-%dT%H:%M:%SZ', 'now'));

COMMIT;
