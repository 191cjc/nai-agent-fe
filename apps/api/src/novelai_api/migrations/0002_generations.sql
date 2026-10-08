BEGIN IMMEDIATE;

CREATE TABLE generation_jobs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    positive_prompt TEXT NOT NULL,
    negative_prompt TEXT NOT NULL,
    settings_json TEXT NOT NULL,
    effective_seed INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('queued', 'running', 'succeeded', 'failed')),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    error_code TEXT,
    image_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX generation_jobs_owner_order ON generation_jobs(user_id, created_at DESC, id DESC);

PRAGMA user_version = 2;
COMMIT;
