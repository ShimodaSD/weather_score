# Wind Score — Agent Guide

## Project overview

Wind Score is a weather-based suitability scoring application. The backend
is a Python FastAPI service, and the planned frontend is a React application.
The API currently resolves an address, fetches current weather from
WeatherAPI, and is beginning to calculate a score for running and cycling.

Treat this repository as a monorepo. Keep backend and frontend changes in
their respective application directories.

## Repository structure

```text
apps/
├── api/                         # FastAPI backend
│   ├── main.py                  # Application, routes, and lifespan
│   ├── weather_api.py           # WeatherAPI integration
│   ├── database.py              # PostgreSQL async connection pool
│   ├── security/                # Bearer-token authentication
│   │   ├── __init__.py
│   │   └── auth.py
│   ├── grade_weather/           # Weather scoring domain code
│   │   ├── main.py
│   │   └── response_weather.json # Example WeatherAPI response
│   ├── pyproject.toml           # API dependencies and tool configuration
│   └── uv.lock                  # Locked API dependencies
└── web/                         # React + TypeScript frontend (Vite)

docs/                            # Project documentation (currently a placeholder)
src/                             # Shared/non-application code (currently empty)
tests/                           # Automated tests (currently empty)
workspace/                       # Working project artifacts (currently empty)
```

The repository-root `pyproject.toml` and `uv.lock` configure backend
dependencies and package `src/weather_score` for editable installation.
Run uv from `apps/api`; it discovers the root project automatically.
Shared application and provider code lives in `src/weather_score` and tests
live in `tests`. API startup instructions are in `apps/api/README.md`.

## Backend: FastAPI

- The API entry point is `apps/api/main.py`.
- Run the API from `apps/api` so its package-relative imports and environment
  files resolve correctly.
- Keep HTTP concerns in routes: parse and validate inputs, call services, and
  serialize responses.
- Keep weather-provider calls in `weather_api.py` or a dedicated adapter.
- Keep scoring rules in `grade_weather/`; do not put scoring formulas in API
  route functions.
- Keep database setup and connection-pool concerns in `database.py`.
- Keep authentication behavior in `security/`.
- Use FastAPI/Pydantic schemas for stable request and response contracts as
  the API grows.
- Public functions should have type hints and async routes must avoid adding
  blocking work where an async implementation is available.

Existing routes include:

- `GET /` — service status.
- `POST /token` — issues the configured bearer token after credential checks.
- `GET /score/run?address=...` — scores weather and elevation without pace.
- `POST /grade/run?address=...` — scores current conditions with a supplied pace.

Geocoding is internal to scoring; the former standalone geocoding, workout-type
scoring, and paginated activity-summary list routes have been removed.
Profile and activity-grade tables are initialized during API startup.
Compose first runs `scripts/initialize_postgres.py` to apply the schema-only
snapshots in `apps/api/sql/` to both databases; it never runs Garmin sync during
startup. `make postgres-init` applies the same snapshots manually. Existing
objects and data are preserved; these snapshots do not migrate changed tables.
See `docs/postgres-schema.md`. Initializer tests are in
`tests/test_initialize_postgres.py`.

Routes included through `protected_api` require the bearer token. Preserve
that behavior unless the authentication design is intentionally changed.

## Weather response contract

`apps/api/grade_weather/response_weather.json` is the example payload returned
by WeatherAPI. Its top-level shape is:

```text
location
└── name, region, country, lat, lon, tz_id, localtime_epoch, localtime

current
├── condition
│   └── text, icon, code
├── temperature: temp_c, temp_f, feelslike_c, feelslike_f
├── wind: wind_kph, wind_mph, wind_degree, wind_dir, gust_kph, gust_mph
├── moisture/precipitation: humidity, precip_mm, precip_in
├── pressure/visibility: pressure_mb, pressure_in, vis_km, vis_miles
├── sunlight: is_day, cloud, uv
└── rain/snow flags and probabilities
```

For scoring, prefer a normalized internal model with consistent units:

- temperature: Celsius
- wind speed and gusts: km/h
- humidity: percentage from 0 to 100
- precipitation: millimetres
- UV: UV index
- wind direction: degrees and/or the provider’s compass direction
- gust: 

Do not couple the scoring engine to WeatherAPI field names. Validate missing,
negative, or out-of-range values explicitly; do not silently convert missing
values to zero.

## Scoring rules

Scores should be deterministic and remain in the range 0–100, where 0 is the
worst and 100 is ideal. Calculate factors independently where practical
(temperature, humidity, wind, precipitation, UV, and cloud cover), then
combine them using documented weights or thresholds. Any scoring change must
include tests for ideal, poor, boundary, invalid, missing, and extreme values.

## Frontend: React

For UI design work, use `apps/web/.agents/skills/ui-ux-pro-max/SKILL.md` and
its bundled scripts and data. Run frontend package commands with pnpm.

The React application belongs in `apps/web`. Keep API calls in a small client
or service layer rather than scattering `fetch` calls through components.
Frontend code should consume the documented API contract, display loading and
error states, and not reimplement backend scoring rules. Keep API URLs and
other environment-specific configuration outside source code.
The Activities dashboard loads `GET /activities/index` for its lightweight
list, `GET /activities/{id}/summary` for a selection, and `GET /activities/{id}`
on the full detail page. All three require the bearer token. Dashboard client
contracts are checked in `apps/web/src/api.test.ts`.
The `#predictions` page uses the protected
`GET /activities/running/predictions` contract. Its calculation lives in
`src/weather_score/application/running_predictions.py` and is tested in
`tests/scores/test_running_predictions.py` and `tests/api/test_activities.py`.
Chart conversion is checked in `apps/web/src/activityChart.test.ts`; run it with
the frontend `pnpm test` command.
Dashboard sync and grade interactions are checked by
`apps/web/tests/activities.browser.cjs`; see `apps/web/README.md` for the
development-server and existing Playwright requirements.
Both **Get new data** buttons poll protected `GET /activities/sync/status`
on page entry and every 30 seconds for live downloaded/total file counts and
the download/import phase, including syncs already running after navigation. Progress
comes from `scripts/download_garmindb.py` and stays in the single API process.
Coverage is in `tests/test_download_garmindb.py`, `tests/api/test_garmin.py`,
the activity API/client tests, and the browser sync check. See
`docs/garmin-sync.md` for file-count semantics and GarminDB compatibility.
Activity details include a TSS calculator using protected
`GET /activities/{id}/tss` and `src/weather_score/application/training_stress.py`.
TSS is training load and may exceed 100; the 0–100 rule applies to weather
suitability only. Running results are labelled average-pace estimates; cycling
requires explicit NP, FTP and timer duration. See `docs/training-stress.md`
for five research sources. Tests live in `tests/scores/test_training_stress.py`,
`tests/api/test_activities.py`, and `apps/web/src/api.test.ts`, with the shared
contract in `tests/contracts/activity_tss.json`.
Activity TSS is read-only and calculated automatically. With no query inputs,
`GET /activities/{id}/tss` uses the saved `athlete_profile` heart-rate threshold
(initially 157 bpm). The authenticated `#profile` page uses `GET /profile` and
`PUT /profile` to store the athlete's name and threshold in the application
database. The table has one row for the application's single configured account.
Profile API/persistence tests live in `tests/api/test_profile.py`; client checks
live in `apps/web/src/api.test.ts`. Missing HR is an error, not a zero load.
The dashboard's weekly TSS card calls protected `GET /activities/tss/weekly`
with `week_of` set to the browser's current local date. It sums Monday–Sunday
activity estimates using the saved threshold and reports excluded activities.
Coverage is in `tests/scores/test_training_stress.py`,
`tests/api/test_activities.py`, and `apps/web/src/api.test.ts`.

## Configuration and security

- For local development and verification, load environment variables from
  the repository-root `.env`; reference the file
  in commands without copying, displaying, or committing its contents.
- Never commit `.env` files, API keys, passwords, access tokens, or database
  credentials.
- Use environment variables for WeatherAPI, PostgreSQL, and auth settings.
- Do not make real external API requests in unit tests; mock Nominatim and
  WeatherAPI responses using the example JSON where appropriate.
- Avoid logging credentials or complete authorization headers.

## Verification

When working on the API, run commands from `apps/api` and use the project’s
`uv` environment, for example:

```bash
uv sync
uv run uvicorn main:app --reload
uv run pytest ../../tests
uv run ruff check ../../src . ../../tests
```

Run frontend commands from `apps/web`: `pnpm install`, `pnpm dev`,
`pnpm test`, and `pnpm build`. Setup and proxy configuration are documented
in `apps/web/README.md`. The first page uses the public
`POST /grade/run?address=...`; the client is in `apps/web/src/api.ts`. The API
response and frontend client share `tests/contracts/run_grade.json` as a contract check.
Keep all frontend secrets out of `VITE_` variables.
Update this guide when shared schemas, tests, or build commands are added.

## Python documentation convention

- Follow the function naming convention in `docs/function-naming.md`.
- Do not add inline or block `#` comments to Python files.
- Runtime docstrings may document public modules, types, and functions.
- Put implementation rationale, equations, research citations, limitations,
  and change notes in Markdown files under `docs/`.

## Definition of done

A change is complete when it is placed in the correct app layer, preserves
the API/security contract, has tests for changed behavior, does not expose
secrets, and has been checked with the relevant backend or frontend tooling.

The Activities dashboard charts twelve Monday–Sunday weeks using protected
`GET /activities/training/weekly?week_of=YYYY-MM-DD`. Running and cycling kilometres
are separate; TSS combines available estimates using the saved profile threshold.
Empty weeks are zero; missing or invalid distances are null, and excluded TSS
activities are counted. Aggregation lives in
`src/weather_score/application/weekly_training.py`, covered by
`tests/scores/test_weekly_training.py`, `tests/api/test_activities.py`, and the
frontend client tests. The chart includes an expandable data table.

UI/UX regression coverage in `apps/web/tests/activities.browser.cjs` includes
skip-link routing, Profile navigation, route titles/focus, responsive overflow,
and keyboard chart controls/data. Run with the existing Playwright setup from
`apps/web/README.md`. The full-detail chart exposes a recorded-value table;
weekly sport bars use solid/striped patterns as well as colors.

`GET /activities/index` includes nullable `distance_km` for the dashboard's
current Monday–Sunday running + cycling distance card. Other sports are excluded; missing
distances are counted and disclosed. The lightweight query still avoids joins.

## Review guidelines

For GitHub pull-request reviews, evaluate new and changed code for performance
as well as correctness:

- Check unnecessary API calls, repeated database queries, missing query bounds,
  redundant React rendering, inefficient loops, and avoidable memory use.
- Prefer the simplest efficient implementation that preserves validation,
  error handling, security, and accessibility.
- Measure meaningful bottlenecks when practical. Identify the affected workload
  and user impact; distinguish measured results from suspected risks.
- Do not claim an implementation is the fastest without benchmark evidence.
  Avoid speculative optimizations and dependencies without a demonstrated need.

Codex PR review notifications use `.github/workflows/main.yml` and
`scripts/notify_openbot.py`. Setup and webhook contract are documented in
`docs/openbot-notifications.md`; mocked checks live in `tests/test_notify_openbot.py`.
