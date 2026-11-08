# Supabase database

The default Compose configuration connects the backend to one Supabase database.
Application tables remain in `public`; GarminDB tables remain in their Garmin
schemas. The separate local configuration uses two databases.

Keep `.env.supabase` private and out of version control. It supplies `DB_HOST`,
`DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, and `DB_NAME_GARMIN`. Both names
must identify the same database. Use the Supabase session pooler on port 5432
when Docker cannot reach the IPv6-only direct endpoint. Store the Supabase CA
certificate at `workspace/supabase/ca.crt`.

Start the application with:

```sh
docker compose up -d
```

The override enforces `verify-full` for PostgreSQL connections. The app enables
row-level security on its public tables in shared mode; anonymous and
authenticated API roles do not need access. Garmin schemas must remain
unexposed to the Data API. Keep the Data API disabled unless it is needed and
its access rules have been reviewed.

To use the separate local databases instead, omit the automatic override:

```sh
docker compose -f compose.yaml up -d
```

For dashboard Garmin sync, set `GARMIN_CONNECT_SECRET_FILE` in `.env` to the
absolute path of a protected file containing the Personal API key. Compose
mounts that file read-only. The existing `GARMIN_CONNECT` environment variable
still takes precedence when it is set; neither value belongs in source control.
The dashboard allows up to 30 minutes for a Garmin sync because importing
existing activity files over the remote database connection can take longer
than a local import.

The original local PostgreSQL database and Garmin files are not synchronized
with future Supabase changes. Supabase Free has no automatic database backups:
export both schema and data regularly, store backups separately, and test a
restore. The schema snapshots are not versioned migrations.

## Archiving expired data

`uv run --no-sync python scripts/archive_old_data.py` archives data older than
one year. It restores a full snapshot into a newly named local PostgreSQL
database and compares every row before deleting expired remote records in a
transaction. It stops without deleting if the tables change, the backup cannot
be restored, or the data differs. It retains records without a usable date,
profile and device configuration, and activities still being graded. Summaries
are retained until their entire period is older than the cutoff.

The local archive databases are independent snapshots and accumulate over time;
each may contain a full copy of the remote data. Keep all of them unless their
contents have been independently preserved. Old activities no longer appear in
the Supabase-backed dashboard. Garmin imports can reintroduce old files; the
weekly archive will process those again. Local archives are not a substitute
for tested backups stored separately from this computer.
