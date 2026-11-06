BEGIN IMMEDIATE;

-- Owner-edited training captions of training-set groups: replace the content tags the
-- export derives from the frozen item prompt. Training only; never sent to a provider,
-- so the frozen group parameters and any re-run stay unchanged.
CREATE TABLE caption_overrides (
    user_id TEXT NOT NULL REFERENCES users(id),
    job_id TEXT NOT NULL REFERENCES generation_jobs(id) ON DELETE CASCADE,
    caption TEXT NOT NULL CHECK(length(caption) BETWEEN 1 AND 3000),
    updated_at INTEGER NOT NULL,
    PRIMARY KEY(user_id, job_id)
);

CREATE INDEX caption_overrides_job ON caption_overrides(job_id);

PRAGMA user_version = 12;
COMMIT;
