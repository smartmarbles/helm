-- Helm runtime store — canonical schema (workflow-scoped persistent tier).
-- spec015 Task 2.1 / spec §5.1 (storage tiers) + §5.3 (concurrency & locking).
--
-- Scope: this file covers ONLY the workflow-scoped persistent tier. Turn-level
-- ephemeral fields are never persisted here; the session-scoped routing pointer
-- (session_active_workflow_id) is a separate tier and is intentionally omitted.
--
-- WAL is MANDATORY (spec015 Watch Out #15 / Task 2.1): a write lock held by one
-- session's hook handler must not block other sessions' synchronous hook
-- callbacks. journal_mode=WAL MUST be the first statement executed on every
-- fresh database connection. busy_timeout is a safety net for residual lock
-- contention after WAL mode is enabled.
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- schema_migrations: applied-migration bookkeeping (idempotent re-runs).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT    NOT NULL PRIMARY KEY,
    applied_at  TEXT    NOT NULL
);

-- ---------------------------------------------------------------------------
-- workflows: the workflow identity record (spec §5.1 minimum data model).
-- Authoritative home for lifecycle class, supersede linkage, owner lease,
-- optimistic-concurrency revision, prior-state pointer, and terminal metadata.
-- Composite identity key is (session_id, workflow_id) per spec §5.1 #1.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS workflows (
    session_id                      TEXT    NOT NULL,
    workflow_id                     TEXT    NOT NULL,

    -- Lifecycle class (spec §5.1 #4).
    workflow_lifecycle              TEXT    NOT NULL DEFAULT 'non_terminal_active'
        CHECK (workflow_lifecycle IN (
            'non_terminal_active', 'non_terminal_suspended', 'terminal')),

    -- Current FSM state and persisted prior non-terminal state (GAP-011 /
    -- POL-014C). prior_non_terminal_fsm_state is authoritative state: written on
    -- TR-002/TR-033, cleared on TR-003/TR-034, and never derived from elsewhere.
    fsm_state_ref                   TEXT    NOT NULL
        CHECK (fsm_state_ref GLOB 'ST-[0-9][0-9][0-9]'),
    prior_non_terminal_fsm_state    TEXT
        CHECK (prior_non_terminal_fsm_state IS NULL
               OR prior_non_terminal_fsm_state GLOB 'ST-[0-9][0-9][0-9]'),

    -- Predecessor/successor linkage for `supersede` (spec §5.1 #7).
    predecessor_workflow_id         TEXT,
    successor_workflow_id           TEXT,

    -- Owner lease lock (spec §5.3 #1). owner_lock_active holds the agent NAME
    -- (audit identity, e.g. ARTHUR), not a role — policy resolves the role via
    -- registry lookup (Watch Out #4). null when no lock is held.
    owner_lock_active               TEXT,
    owner_lock_token                TEXT,
    owner_lock_acquired_at          TEXT,
    owner_lock_expires_at           TEXT,

    -- Optimistic-concurrency revision (spec §5.3 #3): monotonic CAS counter.
    revision                        INTEGER NOT NULL DEFAULT 1
        CHECK (revision >= 1),

    -- Boundary-event metadata for the transition that produced this record
    -- (spec §5.1 #6). On every terminal transition this MUST be 'terminalize'
    -- (POL-014B); enforced by the lifecycle evaluator, not the schema.
    boundary_event                  TEXT
        CHECK (boundary_event IS NULL OR boundary_event IN (
            'new', 'supersede', 'suspend', 'resume', 'terminalize')),

    -- Immutable terminal metadata (spec §5.1 #9). Once is_terminal flips to 1
    -- these fields are write-once; immutability is enforced by the adapter.
    is_terminal                     INTEGER NOT NULL DEFAULT 0
        CHECK (is_terminal IN (0, 1)),
    terminal_state                  TEXT
        CHECK (terminal_state IS NULL
               OR terminal_state IN ('ST-900', 'ST-901', 'ST-902')),
    terminalized_at                 TEXT,
    terminal_reason                 TEXT
        CHECK (terminal_reason IS NULL
               OR terminal_reason IN ('success', 'stop', 'reject', 'superseded')),

    -- Creation audit (spec §5.1 #10). created_by holds the agent NAME or the
    -- literal SYSTEM — an identity record, never collapsed to a role.
    created_at                      TEXT    NOT NULL,
    created_by                      TEXT    NOT NULL,

    PRIMARY KEY (session_id, workflow_id),

    -- A workflow cannot point its own predecessor/successor at itself.
    CHECK (predecessor_workflow_id IS NULL
           OR predecessor_workflow_id <> workflow_id),
    CHECK (successor_workflow_id IS NULL
           OR successor_workflow_id <> workflow_id),

    -- spec §5.3 #2: suspended, inactive, and terminal workflows MUST NOT hold
    -- an active owner lease.
    CHECK (workflow_lifecycle = 'non_terminal_active'
           OR owner_lock_active IS NULL),

    -- Terminal flag and lifecycle class are kept consistent.
    CHECK ((is_terminal = 1) = (workflow_lifecycle = 'terminal'))
);

CREATE INDEX IF NOT EXISTS idx_workflows_predecessor
    ON workflows (session_id, predecessor_workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflows_successor
    ON workflows (session_id, successor_workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflows_lifecycle
    ON workflows (session_id, workflow_lifecycle);

-- ---------------------------------------------------------------------------
-- blackboard_rows: the canonical Profile #4 control-plane record (POL-051/052,
-- blackboard-row.schema.v1.json). One row per workflow. Holds the row-scoped
-- fields (item, lifecycle stage, gate outcomes, row audit). Workflow-scoped
-- fields (linkage, owner lock, revision, terminal, prior_non_terminal_fsm_state)
-- live in `workflows` and are joined at read time to avoid duplicate state /
-- drift (spec §5.1 closing note; Watch Out #7).
-- ---------------------------------------------------------------------------
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

    -- Hard-gate outcomes (spec §5.1 #5). Evaluated in ascending fail-fast order
    -- (POL-054). Each outcome is one of the gateOutcome enum values.
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

    -- First-failure identifier (spec §5.1 #5); null when no gate has failed.
    gate_first_failure_id   TEXT
        CHECK (gate_first_failure_id IS NULL
               OR gate_first_failure_id GLOB 'BG-[0-9][0-9][0-9]'),

    required_gates_passed   INTEGER NOT NULL DEFAULT 0
        CHECK (required_gates_passed IN (0, 1)),

    -- Row audit columns. revision is the authoritative CAS counter and is held
    -- on `workflows`; it is joined in when serializing the contract's audit
    -- block, not duplicated here.
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

-- ---------------------------------------------------------------------------
-- mutation_audit: append-only mutation audit trail (spec §5.1 #10). Records
-- actor, operation, revision delta, and correlation id for each committed
-- mutation. operation_id (the idempotency key, spec §5.3 #4) is populated by the
-- locking layer (Task 2.4) and is nullable here.
-- ---------------------------------------------------------------------------
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
