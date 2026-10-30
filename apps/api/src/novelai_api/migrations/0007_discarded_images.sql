BEGIN IMMEDIATE;

CREATE TABLE discarded_images (
    user_id TEXT NOT NULL REFERENCES users(id),
    job_id TEXT NOT NULL REFERENCES generation_jobs(id) ON DELETE CASCADE,
    image_index INTEGER NOT NULL CHECK(image_index BETWEEN 0 AND 7),
    created_at INTEGER NOT NULL,
    PRIMARY KEY(user_id, job_id, image_index)
);

CREATE INDEX discarded_images_job ON discarded_images(job_id);

PRAGMA user_version = 7;
COMMIT;
