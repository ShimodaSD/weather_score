# PostgreSQL schema initialization

Compose runs `scripts/initialize_postgres.py` before Uvicorn. It creates schema
objects without importing GarminDB or contacting Garmin. Compose provisions the
databases themselves through the PostgreSQL entrypoint. To run manually from
the repository root, loading the repository-root `.env`:

```bash
make postgres-init
```

`apps/api/sql/application.sql` targets `DB_NAME`; `apps/api/sql/garmin.sql`
targets `DB_NAME_GARMIN`. These must be separate databases. Each database is
initialized transactionally under an advisory lock, preserving existing data
and preventing concurrent initializers from racing.

The snapshots came from PostgreSQL 17 using
`pg_dump --schema-only --no-owner --no-privileges --no-comments`, with guards
added for existing objects. They contain no activity data or credentials.
They include 24 tables, 9 views, 4 enum types, 1 sequence, and primary, unique,
check, and foreign-key constraints. Garmin definitions target GarminDB 3.9.0.
The API still seeds the default athlete profile and applies its existing
activity-grade migration at startup.

Repeated initialization fills in missing objects without changing existing
table columns or enum values. These snapshots are not migrations: future
schema changes require explicit migrations and updated snapshots. GarminDB
populates its schema attribute rows during sync.

Activity lists stay empty until sync runs. Use `make garmin-sync` or the
**Get new data** button to populate or refresh data. Startup never runs
`sync_garmindb.py --if-needed`.

## Table inventory

| Database | Table |
| --- | --- |
| DB_NAME | `public.activity_grades` |
| DB_NAME | `public.athlete_profile` |
| DB_NAME_GARMIN | `garmin._attributes` |
| DB_NAME_GARMIN | `garmin.attributes` |
| DB_NAME_GARMIN | `garmin.daily_summary` |
| DB_NAME_GARMIN | `garmin.device_info` |
| DB_NAME_GARMIN | `garmin.devices` |
| DB_NAME_GARMIN | `garmin.files` |
| DB_NAME_GARMIN | `garmin.hrv` |
| DB_NAME_GARMIN | `garmin.resting_hr` |
| DB_NAME_GARMIN | `garmin.sleep` |
| DB_NAME_GARMIN | `garmin.sleep_events` |
| DB_NAME_GARMIN | `garmin.stress` |
| DB_NAME_GARMIN | `garmin.weight` |
| DB_NAME_GARMIN | `garmin_activities._attributes` |
| DB_NAME_GARMIN | `garmin_activities.activities` |
| DB_NAME_GARMIN | `garmin_activities.activities_devices` |
| DB_NAME_GARMIN | `garmin_activities.activity_laps` |
| DB_NAME_GARMIN | `garmin_activities.activity_records` |
| DB_NAME_GARMIN | `garmin_activities.activity_splits` |
| DB_NAME_GARMIN | `garmin_activities.climbing_activities` |
| DB_NAME_GARMIN | `garmin_activities.cycle_activities` |
| DB_NAME_GARMIN | `garmin_activities.steps_activities` |
| DB_NAME_GARMIN | `garmin_activities.paddle_activities` |
