BEGIN IMMEDIATE;

-- Owner-chosen concurrency of a GPT image run (NULL = the lane's configured maximum).
-- Not part of the frozen definition: it may change while the run is unfinished, and the
-- scheduler always caps it by the server's NAI_GPT_IMAGE_CONCURRENCY.
ALTER TABLE style_experiment_runs
ADD COLUMN parallelism INTEGER CHECK(parallelism IS NULL OR parallelism BETWEEN 1 AND 16);

PRAGMA user_version = 11;
COMMIT;
