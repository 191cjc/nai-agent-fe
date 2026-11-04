BEGIN IMMEDIATE;

-- Owner-chosen display names for saved experiments / training sets. Kept apart from
-- the frozen run definition so renaming never changes a run or its retry identity.
CREATE TABLE experiment_names (
    user_id TEXT NOT NULL REFERENCES users(id),
    run_id TEXT NOT NULL,
    name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 80),
    named_at INTEGER NOT NULL,
    PRIMARY KEY(user_id, run_id)
);

PRAGMA user_version = 8;
COMMIT;
