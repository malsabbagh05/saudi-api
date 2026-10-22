# Database

PostgreSQL owns the project's control state (`AGENTS.md`, "Architecture"). Alembic
owns its schema. This document owns how migrations are numbered, written and
released, and the commands that `AGENTS.md` ("SQL work") requires.

## Database migrations

`alembic.ini` and `migrations/` are the files `uv run alembic init migrations`
generates. `env.py` reads the database URL from the configuration's
`sqlalchemy.url`, and `tests/support/postgres.py` sets that option for each test
database, so keep it that way: supply the deployed URL by setting the option (for
example from the environment, before `env.py` connects), not by changing `env.py` to
read the URL from somewhere else. Replace the placeholder URL in `alembic.ini`.

Revision IDs are sequential: `<UTC date>_<NNNN>`, one more than the current head.
Create a migration with
`uv run alembic revision --rev-id <YYYYMMDD>_<NNNN> -m "<summary>"`; Alembic sets
`down_revision` to the current head and names the file `<rev-id>_<slug>.py`.

Parallel pull requests can take the same number. The `Check migration head` step
sees only the pull request's own graph, so it cannot catch a migration merged after
it passed. Recheck the head right before merging (`merge-on-green --alembic` does);
if another pull request merged a migration first, renumber yours to the next free
number, set `down_revision` to the new head, and rebase.

A migration owns its DDL. It never imports the application's mapped models and
never calls `create_all` or `drop_all`: those build the schema the models describe
today, not the schema at the migration's own revision.

Removing a column or table that released code reads or writes takes two pull
requests ([Parallel Change](https://martinfowler.com/bliki/ParallelChange.html)):
first merge and deploy the change that stops using it, then drop it in a later
migration. The drop locks the table first and restores the empty schema on
downgrade. It deletes any rows still left, so its pull request states what they are
and how many the shared development environment holds.

A migration that deletes, updates or backfills rows of a large table states in its
pull request how many rows it touches in the shared development environment and how
long that takes, from a read-only count or `EXPLAIN`. A test that upgrades populated
data from the deployed revision to head belongs in the `tests` block of every pull
request that adds a migration.

## SQL performance

The shared development environment's PostgreSQL loads `pg_stat_statements` and
`auto_explain`; the test PostgreSQL loads `pg_stat_statements`
(`tests/support/postgres.conf`). Read a shared database in a read-only session:

```bash
PGOPTIONS='-c default_transaction_read_only=on' psql "$DATABASE_URL"
```

The statements that use the most database time, with the pages each call reads:

```sql
SELECT round(total_exec_time::numeric / 1000) AS total_s, calls,
       round(mean_exec_time::numeric, 1) AS mean_ms,
       (shared_blks_hit + shared_blks_read) / calls AS pages_per_call,
       left(regexp_replace(query, '\s+', ' ', 'g'), 200) AS query
FROM pg_stat_statements
WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
ORDER BY total_exec_time DESC LIMIT 20;
```

The numbers add up from `stats_reset` in `pg_stat_statements_info`, so a statement
that was fixed keeps its old total. To see what a statement costs now, read its row
twice, a minute apart, and divide the differences. Compare `pages_per_call` with the
table's page count (`pg_relation_size('<table>') / 8192`): an equal number means the
statement reads the whole table on each call.

The plan of one statement, as the code sends it:

```sql
EXPLAIN (ANALYZE, BUFFERS, TIMING OFF) SELECT ...;
```

`ANALYZE` runs the statement, so use it for a `SELECT` only, and without its
`FOR UPDATE` clause. For a write, read plain `EXPLAIN`. A bound parameter can hide an
index from the planner: a prepared statement cannot prove a partial index's predicate
from a parameter, so write the value of such a predicate as a literal in the query.

`pg_stat_user_indexes.idx_scan` shows whether an index was ever used, and
`pg_stat_user_tables.seq_scan` how often a table was read whole.

Configure `auto_explain` in the shared development environment to log the plan of
each statement slower than one second, with row and buffer counts and without
parameter values (`auto_explain.log_min_duration = '1s'`,
`auto_explain.log_analyze = on`, `auto_explain.log_buffers = on`,
`auto_explain.log_parameter_max_length = 0`;
[PostgreSQL: auto_explain](https://www.postgresql.org/docs/current/auto-explain.html)).
Each plan in the server log starts with a `duration: <ms> ms  plan:` line.

A test proves that a statement can use its index: it records the statement the code
sends, runs `EXPLAIN` on it in the test database, and asserts the plan uses the index
and does not sort or scan the table.
