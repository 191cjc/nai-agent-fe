BEGIN IMMEDIATE;

CREATE TABLE prompt_snapshots (
    user_id TEXT NOT NULL REFERENCES users(id),
    id TEXT NOT NULL,
    name TEXT NOT NULL,
    entries_json TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY(user_id, id)
);

CREATE INDEX prompt_snapshots_owner_order
ON prompt_snapshots(user_id, created_at DESC, id DESC);

PRAGMA user_version = 4;
COMMIT;
