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

The original local PostgreSQL database and Garmin files are not synchronized
with future Supabase changes. Supabase Free has no automatic database backups:
export both schema and data regularly, store backups separately, and test a
restore. The scheduled archival routine remains disabled until its copy,
verification, deletion and Garmin re-import behavior have been implemented and
tested. The schema snapshots are not versioned migrations.
