BEGIN IMMEDIATE;

-- Upstream signed download links of a job's images (index-aligned), recorded after a
-- successful provider call. Server-private: links carry signatures and are never sent to
-- the browser. Local PNG files remain the source of truth; links expire upstream.
CREATE TABLE provider_image_links (
    job_id TEXT PRIMARY KEY REFERENCES generation_jobs(id) ON DELETE CASCADE,
    links_json TEXT NOT NULL CHECK(length(links_json) <= 65536),
    recorded_at INTEGER NOT NULL
);

PRAGMA user_version = 15;
COMMIT;
