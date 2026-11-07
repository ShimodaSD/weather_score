# Wind Score API

From this directory, install the project and start the API:

```bash
uv sync
uv run uvicorn main:app --reload
```

Dependencies and packaging are configured in the repository-root `pyproject.toml`.
uv discovers that project from this directory and installs `src/weather_score`
as an editable package. For IDE launches, select the repository-root
`.venv/bin/python` interpreter.

Run checks from this directory with `uv run pytest ../../tests` and
`uv run ruff check ../../src . ../../tests`.

## Docker

From the repository root, run `docker compose up -d --build backend`.
The image installs dependencies in `/opt/venv`, outside the mounted source tree.
Dependency layers and the uv download/build cache are reused across source edits.
Startup uses that installed environment without syncing packages; rebuild the
backend image after changing `pyproject.toml` or `uv.lock`.

Compose creates application and Garmin tables from schema-only SQL snapshots
before starting Uvicorn. Startup does not download or import Garmin data.
Run `make postgres-init` from the repository root to create the tables manually.
Existing tables and data are preserved. See [PostgreSQL schema](../../docs/postgres-schema.md)
and [Garmin setup](../../docs/garmin-sync.md).

API startup initializes the athlete profile and upgrades activity-grade storage
once per process. Requests no longer run these schema and data setup statements.
With the supported single API process, startup marks interrupted grades as failed
so they can be retried. Running multiple API processes requires shared job
ownership and recovery before enabling this behavior.

The unused `GET /address-to-lat-long`, `GET /score/run/by-type`, and
`GET /activities` routes have been removed. Geocoding remains part of both
running-score routes. Activity clients use `/activities/index` and
`/activities/{id}/summary` instead of the former summary list.

Set `GARMIN_CONNECT` in root `.env` to a Garmin Personal API key and configure
`GARMINDB_PATH` for local activity files. The dashboard's protected
`POST /activities/sync` downloads from the official Personal API, then runs the
local GarminDB JSON/FIT parser and PostgreSQL import. `make garmin-sync` runs the
same process. No Garmin username/password login is used. See
[Garmin sync](../../docs/garmin-sync.md) for setup, sync windows and progress.
