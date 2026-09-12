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

Set `GARMINDB_PATH` to GarminDB's `garmin_activities.db`, then upload every
activity to PostgreSQL with `POST /garmin/sync`. The service reads and writes
activities in bounded batches without blocking the API event loop.

Run Uvicorn with `--log-level debug` to log each completed sync batch. Failures
log the phase, batch number, and synchronized row count; API responses distinguish
invalid GarminDB input (`422`) from unavailable PostgreSQL (`503`).
