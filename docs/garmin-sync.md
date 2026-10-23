# GarminDB sync

## Docker Compose

Compose uses the repository-root `.env`, its own PostgreSQL service, and Garmin
files inside this project. It does not mount your host home directory.

Compose mounts `/Users/shimoda/.GarminDb/GarminConnectConfig.json` read-only at
`/app/GarminConnectConfig.json`. Change the bind source in `compose.yaml` if your
configuration lives elsewhere. The source file must exist, with your
Garmin username in `credentials.user` and SQLite as the database type. Set
`SECRET_GARMIN` in `.env` to your Garmin password. Each sync generates
`/root/.GarminDb/GarminConnectConfig.json` from that file, injecting
the password and project data path. The generated file has mode `0600`;
The source configuration and `.env` must stay out of Git. Existing password-file and
secure-password settings are replaced by the `.env` password. Existing session
files are managed by GarminDB inside the backend container.

Place any existing downloaded Garmin data and SQLite databases in
`workspace/garmin/HealthData/` (the activities database belongs at
`HealthData/DBs/garmin_activities.db`). If starting fresh, GarminDB downloads data
using the start dates in your configuration. These directories are ignored by Git.

```bash
docker compose up -d
docker compose exec -w /app backend make garmin-sync
```

Compose supplies the container database path and mounts the project Garmin
configuration at `/app/GarminConnectConfig.json`. It disables the optional bootstrap path;
reuse existing data by placing it in the project directory above. Subsequent
refreshes use the same command or the dashboard's **Get new data** button.
Before starting the API, Compose runs `scripts/initialize_postgres.py` to create
all tables from schema-only SQL snapshots. Startup never waits for a Garmin
download or import. Activity lists are empty until the first sync completes.
Run the explicit sync command above, or use **Get new data**, to populate or
refresh data after startup. See [PostgreSQL schema](postgres-schema.md).

### Download progress

**Get new data** shows a live file counter and remaining files on Activities and
Grades. While Garmin is logging in and listing activities, it shows “Checking
Garmin for new data”; the total is unknown until that list arrives. The counter
includes missing activity summary JSON, detail JSON and downloaded ZIP archives
for this sync's configured activity window. Existing files that GarminDB skips
are excluded. A ZIP counts as one transfer, regardless of extracted FIT files.
This is a file count, not a byte count or a count of all history on Garmin.

After transfers and extraction finish, the display changes to importing.
The final activity count appears after the PostgreSQL import and TSS update.
Failed transfers do not advance the counter. Failed progress requests display
an unavailable message while the sync request continues.

The protected `GET /activities/sync/status` endpoint returns `phase`,
`downloaded_files`, and nullable `total_files`; both pages query immediately, then every 30 seconds
while authenticated, including on page entry. An active sync is restored after
a refresh or navigation, and disables duplicate sync requests. When a restored
sync changes from active to complete, the page reloads its activity data and
dashboard totals once. Repeated complete responses do not reload data; syncs
started on the page continue to refresh through their POST completion path.
The existing POST response is unchanged.
Progress and the sync lock belong to the single API process used by Compose;
multiple API workers would require shared job state. The downloader instrumentation
targets the pinned GarminDB 3.9 implementation and must be reviewed on upgrades.

## Running without Docker

The project keeps Garmin credentials and session files in GarminDB's standard
`~/.GarminDb` directory. Install no separate GarminDB checkout or duplicate
configuration.

The Docker backend mounts
`/Users/shimoda/.GarminDb/GarminConnectConfig.json` read-only at
`/app/GarminConnectConfig.json`, which the sync command uses in the
container. The source file must already exist. After changing the mount, apply
it with `docker compose up -d --no-deps backend`. This mounts only the config;
the configured activity-data paths must also be accessible inside Docker.

In `~/.GarminDb/GarminConnectConfig.json`, use SQLite and set the data directory.
For example, this stores data below `/Users/me/dbs/garmindb/HealthData`:

```json
{
  "db": {"type": "sqlite"},
  "directories": {"relative_to_home": false, "base_dir": "HealthData"}
}
```

Run the command from `/Users/me/dbs/garmindb`, or let the project command do so
by setting the matching database path:

```bash
export GARMINDB_PATH=/Users/me/dbs/garmindb/HealthData/DBs/garmin_activities.db
export DB_NAME_GARMIN=garmin
```

The command also loads these values from a repository-root `.env` file when it
exists.

For the initial bootstrap, point at an existing valid activities database. The
command copies that database so its activity history is reused:

```bash
GARMINDB_BOOTSTRAP_PATH=/Users/me/old/HealthData/DBs/garmin_activities.db make garmin-sync
```

If no existing databases are available, omit `GARMINDB_BOOTSTRAP_PATH`; the first
run starts from the dates in the GarminDB config. Every later refresh is the same
command:

```bash
make garmin-sync
```

The command downloads activities only, keeps the local SQLite database, and
imports every locally downloaded Garmin data type into `DB_NAME_GARMIN` on the
same PostgreSQL server as `DB_NAME`. GarminDB creates separate `garmin`,
`garmin_activities`, and `garmin_monitoring` schemas. The first PostgreSQL import
processes all local files; later runs import only files from the latest overlap.
After import, the command copies activity names from SQLite into PostgreSQL to
work around GarminDB 3.9 passing numeric JSON IDs to its text primary key.

PostgreSQL imports run through `scripts/import_garmindb.py`, which normalizes
JSON activity IDs to strings before GarminDB looks up or updates activity rows.
This avoids PostgreSQL's `character varying = bigint` error without casting
indexed database columns or rewriting downloaded files. The compatibility fix
targets GarminDB 3.9's shared JSON activity processor; review it when upgrading
GarminDB. FIT import and the SQLite sync keep their original behavior.

Immediately after the name update, the same sync creates the nullable
`garmin_activities.activities.tss` column if needed and recalculates **all**
activities, including older activities and those without names. It reuses the
[heart-rate TSS estimate](training-stress.md) with the threshold saved in
`DB_NAME`'s `athlete_profile` table (157 bpm before a profile is configured).
Unsupported sports or missing/invalid heart rate or elapsed time produce SQL
`NULL`, not zero. A failed database update rolls back the TSS backfill and fails
the sync. Repeated syncs refresh existing values as well as new activities.

The stored column is a snapshot of the last successful sync. After changing the
profile threshold, run sync to refresh stored values; the dashboard and weekly
total already calculate live using the current profile threshold.
