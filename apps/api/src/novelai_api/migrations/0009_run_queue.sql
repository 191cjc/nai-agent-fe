BEGIN IMMEDIATE;

-- Several unfinished runs per owner may now wait in a queue. Each run is pinned to an
-- execution lane: GPT image character runs never wait behind NovelAI work and vice versa.
-- Within one owner's lane, runs advance strictly in creation order.
ALTER TABLE style_experiment_runs
ADD COLUMN lane TEXT NOT NULL DEFAULT 'novelai' CHECK(lane IN ('novelai', 'gpt'));

UPDATE style_experiment_runs SET lane = 'gpt'
WHERE json_extract(definition_json, '$.character.mode') = 'gpt';

DROP INDEX style_experiment_one_active_owner;

CREATE INDEX style_experiment_active_queue
ON style_experiment_runs(user_id, lane, created_at) WHERE status IN ('running', 'stopping');

PRAGMA user_version = 9;
COMMIT;
