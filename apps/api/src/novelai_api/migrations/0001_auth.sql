BEGIN IMMEDIATE;

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE access_tokens (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    token_digest TEXT NOT NULL UNIQUE,
    created_at INTEGER NOT NULL,
    revoked_at INTEGER
);

CREATE TABLE browser_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    token_id TEXT NOT NULL REFERENCES access_tokens(id),
    session_digest TEXT NOT NULL UNIQUE,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    revoked_at INTEGER
);

CREATE INDEX browser_sessions_token_id ON browser_sessions(token_id);
CREATE INDEX browser_sessions_expires_at ON browser_sessions(expires_at);

PRAGMA user_version = 1;
COMMIT;
