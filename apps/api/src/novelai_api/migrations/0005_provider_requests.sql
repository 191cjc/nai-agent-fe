BEGIN IMMEDIATE;

ALTER TABLE generation_jobs ADD COLUMN provider_request_json TEXT;

PRAGMA user_version = 5;
COMMIT;
