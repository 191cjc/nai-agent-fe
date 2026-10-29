BEGIN IMMEDIATE;

CREATE TABLE reference_images (
    user_id TEXT NOT NULL REFERENCES users(id),
    id TEXT NOT NULL,
    sha256 TEXT NOT NULL CHECK(length(sha256) = 64),
    mime_type TEXT NOT NULL CHECK(mime_type IN ('image/png', 'image/jpeg')),
    width INTEGER NOT NULL CHECK(width BETWEEN 64 AND 2048),
    height INTEGER NOT NULL CHECK(height BETWEEN 64 AND 2048),
    byte_size INTEGER NOT NULL CHECK(byte_size BETWEEN 1 AND 8388608),
    source TEXT NOT NULL CHECK(source IN ('upload', 'result')),
    created_at INTEGER NOT NULL,
    PRIMARY KEY(user_id, id)
);

PRAGMA user_version = 6;
COMMIT;
