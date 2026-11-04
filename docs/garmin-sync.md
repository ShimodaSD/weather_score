# Garmin Personal API sync

Sync downloads activities directly from the official [Garmin Connect Personal
API Swagger](https://developer.garmin.com/gc-developer-program/personal/swagger-docs).
GarminDB 3.9 remains the local JSON/FIT parser and database importer; it no longer
logs in to Garmin or makes download requests. Existing PostgreSQL tables,
SQLite history, recorded points, laps, grading, TSS and dashboard contracts are
preserved.

## Configuration and running

Set `GARMIN_CONNECT` in the repository-root `.env` to your **Personal API key**,
not a bearer token. Create the key in Garmin Connect Web. Garmin username,
password, `SECRET_GARMIN`, and the old host config bind mount are no longer needed.
Keep `.env` and downloaded personal data out of Git.

Compose supplies `GARMINDB_PATH` inside `workspace/garmin/HealthData/DBs/`.
Existing files can be reused under `workspace/garmin/HealthData/`, including
`FitFiles/Activities/` and `DBs/garmin_activities.db`.

```bash
docker compose up -d --build

docker compose exec -w /app backend make garmin-sync
```

The dashboard's **Get new data** button calls the same command through protected
`POST /activities/sync`. Startup applies schema snapshots only and does not sync.
The protected progress endpoint remains `GET /activities/sync/status`.

Outside Docker, set `GARMINDB_PATH` to an absolute path ending in
`HealthData/DBs/garmin_activities.db`, configure PostgreSQL variables from
`.env.example`, and run `make garmin-sync`. The command loads root `.env`.
`DB_NAME_GARMIN` must differ from `DB_NAME`. An optional
`GARMINDB_BOOTSTRAP_PATH` copies an existing valid activities SQLite database;
existing databases and history are not replaced.

An existing `~/.GarminDb/GarminConnectConfig.json`, or an explicitly selected
`GARMINDB_CONFIG`, may supply import settings. It is
not required. Sync writes a private import-only configuration under
`HealthData/DBs/config/`, removes Garmin credentials from that generated copy,
and leaves the source config untouched. New databases import in metric units;
stored measurement-system attributes in existing databases are respected.

## Download contract

`src/weather_score/garmin.py` uses these official endpoints:

- `POST /personalapitoken-service/personal-api/personal-api-key/token` with
  `Authorization: ApiKey ...` and `Accept: */*`. The response is a plain-text
  bearer token, retained only in memory for this sync.
- `GET /activitylist-service/activities/search/activities` with `startDate`, `endDate`, `start` and
  `limit`, in pages of at most 99 activities.
- `GET /activity-service/activity/{activityId}` for detail JSON.
- `GET /download-service/files/activity/{activityId}` for the original ZIP.

GET requests use `Authorization: Bearer ...`. Token exchange is performed once
per sync; HTTP failures, including expiry, throttling and upstream errors, fail
the sync rather than silently skipping activities. Each request has a 30-second
timeout, redirects are rejected, and the API retains its 10-minute sync timeout.
An expired or revoked Personal API key must be replaced in `.env`.

Each sync requests activities from the past three calendar months through today,
inclusive, using the server's local date. When the earlier month has fewer days,
the start date is its last day. All matching pages are retrieved, without a
count limit. Existing summary, detail and FIT files are reused independently,
so a partial download is repaired on the next sync within that window. Existing
local history is retained.

The original archive must contain one FIT file, at most 128 MiB uncompressed.
Only its contents are written to `{activityId}.fit`; archive paths are never
extracted. JSON and FIT files are written using temporary files and atomic
replacement. Invalid responses and archives fail before a completed file is
marked downloaded. Non-FIT activities cannot currently be imported through this
path and cause an explicit sync failure.

## Progress and import

While listing activities, the UI shows “Checking Garmin for new data”. The total
then counts missing summary JSON, detail JSON and FIT files in the three-month
window; existing files are excluded. Each successfully saved file advances the
counter. A ZIP's FIT payload counts as one file. Summary JSON comes from the
list response, so this is a saved-file count, not an HTTP-request or byte count.

After downloads finish, progress changes to importing. The existing GarminDB
parser imports SQLite and PostgreSQL, then copies names and recalculates TSS.
It does not make provider requests. The first PostgreSQL import processes all
local files; SQLite import scans local files so downloaded activities are not limited by a latest-file count.
`import_garmindb.py` normalizes JSON identifiers to text for PostgreSQL and uses
metric units for fresh databases lacking a settings FIT file.

Progress and the sync lock remain in the single API process. Both dashboard
pages poll on entry, every 30 seconds while idle and every two seconds during a
sync. Failed downloads stop before import; completed files remain available for
retry. Import failures can leave SQLite or an earlier importer transaction
updated, as before; retrying reuses local files and idempotent imports. The TSS
backfill has its own transaction.

Tests: `tests/test_download_garmin.py`, `tests/test_sync_garmindb.py`,
`tests/test_import_garmindb.py`, and `tests/api/test_garmin.py`. Unit tests never
call Garmin; the provider boundaries are mocked.

## Local API simulation

The minimal caller contract is `postman/contracts/garmin-personal.openapi.json`.
It contains the used subset of the Swagger and the separately documented token
exchange. The stand-in contains synthetic data only. Start it from the repo root:

```bash
postman simulation run postman/simulations/garmin-personal.sim.yaml --port 4511 --no-history
```

Then, from `apps/api`, run:

```bash
GARMIN_SIMULATION_URL=http://localhost:4511/garmin uv run --extra garmin pytest ../../tests/test_download_garmin.py
```

The optional simulation check exercises real HTTP calls, file reuse, invalid
credentials and throttling. It is skipped when the simulation URL is absent.
The synthetic ZIP checks archive handling, not FIT parsing or database import.
The context file beside the simulation records the live and mocked evidence.

## Stored TSS

After the name update, the same sync creates the nullable
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

## Import a downloaded archive

To import a `tar.gz` containing the `Activities/` directory without downloading
from Garmin, copy the archive into the backend container and run the importer:

```bash
docker compose cp /Users/shimoda/db_garmin/garmin-activities-20261101-194904.tar.gz backend:/tmp/garmin-activities.tar.gz
docker compose exec -w /app backend uv run --env-file .env --extra garmin python scripts/restore_garmin_archive.py /tmp/garmin-activities.tar.gz
```

Run only one Garmin import at a time. The script restores missing files without
replacing existing files, rejects conflicts and unsafe archive paths, and runs a
full local GarminDB import into SQLite and PostgreSQL. The transient activity-list
cache is skipped. Existing database records are not removed. Configure
`GARMINDB_PATH`, `DB_NAME`, `DB_NAME_GARMIN`, and the database connection as for
normal sync; a Garmin API key is not needed for this import.

## Back up downloaded activity files

Set `GARMIN_BACKUP_SOURCE` to the downloaded `Activities` directory and `GARMIN_BACKUP_PATH` to the
full destination filename ending in `.tar.gz` in the repository-root `.env`.
From the repository root on the host, run `make garmin-backup`. The archive
contains the downloaded activity files under `Activities/`, and works with the
archive importer above. It does not include the databases or credentials.
The destination must not already exist; choose a new filename for each backup.
Run the backup after downloads have finished so the archive is complete.
