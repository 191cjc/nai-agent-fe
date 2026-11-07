BEGIN IMMEDIATE;

-- Durable, irreversible per-image cleanup intent. A NULL completed_at leaves
-- filesystem cleanup retryable without making the identity servable/restorable.
CREATE TABLE purged_images (
    user_id TEXT NOT NULL REFERENCES users(id),
    job_id TEXT NOT NULL REFERENCES generation_jobs(id) ON DELETE CASCADE,
    image_index INTEGER NOT NULL CHECK(image_index BETWEEN 0 AND 7),
    created_at INTEGER NOT NULL,
    completed_at INTEGER,
    PRIMARY KEY(user_id, job_id, image_index)
);

CREATE INDEX purged_images_job ON purged_images(job_id);

PRAGMA user_version = 13;
COMMIT;
