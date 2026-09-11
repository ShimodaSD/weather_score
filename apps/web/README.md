# Wind Score web

React and TypeScript, built with Vite. Run from `apps/web`:

```bash
pnpm install
pnpm dev
```

Start the backend separately using `apps/api/README.md`. For local verification,
load its configuration without copying secrets into the frontend:

```bash
cd ../api
uv run --env-file /Users/shimoda/repos/grade_activity/weather_score/.env uvicorn main:app --reload
```

Development defaults are checked in as `.env.development`: `pnpm dev` forwards
`/api` to the backend at `http://127.0.0.1:8000` without additional setup.
To use a different backend, copy `.env.example` to `.env.local`, edit
`API_PROXY_TARGET`, and restart Vite. Only public development URLs belong in
the tracked `.env.development` file.

The Vite development proxy forwards `/api` to `API_PROXY_TARGET`. The browser
uses `VITE_API_BASE_URL`. Only public configuration belongs in `VITE_` variables;
they are bundled into the browser application. Do not put backend credentials
or shared access tokens in frontend environment variables.

The page calls `GET /score/run?address=...`, which returns a number from 0 to 100
or an `{ "error": "..." }` response. Scores are computed by the backend. The page
starts empty and does not invent weather observations or score breakdowns.
Cycling is marked as coming soon because no cycling endpoint is currently wired.
Existing backend authentication is unchanged; authorization failures are shown
as errors. No token is embedded or persisted in the frontend.

```bash
pnpm test
pnpm build
pnpm preview
```

Tests mock HTTP responses; no external weather calls are made. Production hosting
must route `/api` to the backend, or configure a public `VITE_API_BASE_URL` and
appropriate backend CORS policy. The Vite proxy only runs during development.
