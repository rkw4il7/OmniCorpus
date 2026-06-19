-- Enable pgvector. Runs once on first data-volume init via
-- docker-entrypoint-initdb.d. If you bring up Postgres another way, run this
-- against the target database manually (root spec.md §7.1).
CREATE EXTENSION IF NOT EXISTS vector;
