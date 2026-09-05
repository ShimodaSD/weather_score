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
└── web/                         # React frontend (currently a placeholder)

docs/                            # Project documentation (currently a placeholder)
src/                             # Shared/non-application code (currently empty)
tests/                           # Automated tests (currently empty)
workspace/                       # Working project artifacts (currently empty)
```

The root `pyproject.toml`, `README.md`, and the application README files are
currently empty. Do not assume root-level Python tooling applies to the API;
use `apps/api/pyproject.toml` and its lockfile for backend dependencies.

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
- `GET /address-to-lat-long?address=...` — geocodes an address with
  OpenStreetMap Nominatim.
- `GET /weather/address?address=...` — geocodes the address and retrieves
  current weather.

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

The React application belongs in `apps/web`. Keep API calls in a small client
or service layer rather than scattering `fetch` calls through components.
Frontend code should consume the documented API contract, display loading and
error states, and not reimplement backend scoring rules. Keep API URLs and
other environment-specific configuration outside source code.

## Configuration and security

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
uv run pytest
uv run ruff check .
```

Run frontend-specific commands from `apps/web` once its React project is
created. Update this guide when the web app, shared schemas, tests, or build
commands are added.

## Python documentation convention

- Do not add inline or block `#` comments to Python files.
- Runtime docstrings may document public modules, types, and functions.
- Put implementation rationale, equations, research citations, limitations,
  and change notes in Markdown files under `docs/`.

## Definition of done

A change is complete when it is placed in the correct app layer, preserves
the API/security contract, has tests for changed behavior, does not expose
secrets, and has been checked with the relevant backend or frontend tooling.
