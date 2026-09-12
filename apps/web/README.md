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

The page signs in through `POST /token`, then calls bearer-protected
`POST /grade/run?address=...` with an average pace such as `5:20`. It shows the
API's score and factor breakdown. Ambiguous addresses return location options;
the selected option is sent back as `latitude` and `longitude` query parameters.
The token stays in page memory and is cleared on sign-out or authorization
failure. No credentials or token are embedded or persisted in the frontend.
Cycling is marked as coming soon because no cycling endpoint is currently wired.

```bash
pnpm test
pnpm build
pnpm preview
```

The grade client test reads `../../tests/contracts/run_grade.json`, which the
backend response test also checks. No external weather calls are made. Production hosting
must route `/api` to the backend, or configure a public `VITE_API_BASE_URL` and
appropriate backend CORS policy. The Vite proxy only runs during development.
