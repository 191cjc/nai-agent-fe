BEGIN IMMEDIATE;

CREATE TABLE style_experiment_runs (
    user_id TEXT NOT NULL REFERENCES users(id),
    id TEXT NOT NULL,
    definition_json TEXT NOT NULL,
    total TEXT NOT NULL,
    next_ordinal TEXT NOT NULL DEFAULT '1',
    processed_count TEXT NOT NULL DEFAULT '0',
    succeeded_count TEXT NOT NULL DEFAULT '0',
    failed_count TEXT NOT NULL DEFAULT '0',
    current_ordinal TEXT,
    current_job_id TEXT,
    seed INTEGER NOT NULL CHECK(seed BETWEEN 1 AND 4294967295),
    status TEXT NOT NULL CHECK(status IN ('running', 'stopping', 'stopped', 'completed')),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    error_code TEXT,
    PRIMARY KEY(user_id, id),
    CHECK((current_ordinal IS NULL) = (current_job_id IS NULL))
);

CREATE UNIQUE INDEX style_experiment_one_active_owner
ON style_experiment_runs(user_id) WHERE status IN ('running', 'stopping');

PRAGMA user_version = 3;
COMMIT;
