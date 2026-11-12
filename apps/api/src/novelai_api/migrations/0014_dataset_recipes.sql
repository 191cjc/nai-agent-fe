BEGIN IMMEDIATE;

-- Owner-private random style-dataset recipes (partitions, options, rules). Generated
-- items freeze their draws inside the run definition, so deleting a recipe never changes
-- an existing training set.
CREATE TABLE dataset_recipes (
    user_id TEXT NOT NULL REFERENCES users(id),
    id TEXT NOT NULL,
    name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 100),
    recipe_json TEXT NOT NULL CHECK(length(recipe_json) <= 1048576),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY(user_id, id)
);

PRAGMA user_version = 14;
COMMIT;
