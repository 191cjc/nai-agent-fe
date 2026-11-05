BEGIN IMMEDIATE;

-- A run may now hold several accepted groups at once (GPT image lane). Each row is one
-- claimed, not yet counted group; reconcile counts it exactly once and deletes it.
-- style_experiment_runs.current_ordinal/current_job_id stay as a mirror of the lowest
-- in-flight ordinal so older readers keep their single-group view.
CREATE TABLE style_experiment_inflight (
    user_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    ordinal TEXT NOT NULL,
    PRIMARY KEY(user_id, run_id, job_id),
    FOREIGN KEY(user_id, run_id) REFERENCES style_experiment_runs(user_id, id)
        ON DELETE CASCADE
);

INSERT INTO style_experiment_inflight (user_id, run_id, job_id, ordinal)
SELECT user_id, id, current_job_id, current_ordinal FROM style_experiment_runs
WHERE current_job_id IS NOT NULL;

PRAGMA user_version = 10;
COMMIT;
