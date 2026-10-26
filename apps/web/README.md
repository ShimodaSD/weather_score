# Wind Score web

React and TypeScript, built with Vite. Use Node.js 24.22.1 LTS (pinned in the
repository-root `.nvmrc` and Docker Compose). With nvm, run `nvm install` and
`nvm use` from the repository root. Run package commands from `apps/web`:

```bash
pnpm install
pnpm dev
```

Start the backend separately using `apps/api/README.md`. For local verification,
load its configuration without copying secrets into the frontend:

```bash
cd ../api
uv run --env-file ../../.env uvicorn main:app --reload
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

The Conditions page calls public `POST /grade/run?address=...` with an average
pace such as `5:20`. It shows the
API's score and factor breakdown. Ambiguous addresses return location options;
the selected option is sent back as `latitude` and `longitude` query parameters.
The header sign-in dialog uses `POST /token` for activities and predictions.
Sign-in sets a signed, HttpOnly browser cookie that expires after one day. The
web app restores the session on reload through `GET /session`, sends the cookie
with protected requests, and clears it through `POST /logout` on sign-out. The
bearer token response remains available to API clients but is not stored by the
web app. Credentials and access tokens are not embedded in frontend assets.
The Activities tab uses the same browser session to load the lightweight
`GET /activities/index` list. Selecting an activity loads its summary from
`GET /activities/{id}/summary`; the full details page at `#activity?aid=...`
loads laps, splits, recorded samples, and devices from `GET /activities/{id}`.
Chart.js shows weekly sport distances and combined TSS on the dashboard, and
heart rate and pace on separate axes on the full detail page. The detail chart
has keyboard-operable series controls and an expandable recorded-value table.
When signed out, the Activities page shows its own sign-in form.
The `#predictions` page calls `GET /activities/running/predictions` and shows
study-modelled 5, 10, 21, and 42 km times or bounded ranges, with links to the
recorded benchmark runs.

```bash
pnpm test
pnpm build
pnpm preview
```

The grade client test reads `../../tests/contracts/run_grade.json`, which the
backend response test also checks. No external weather calls are made. Production hosting
must route `/api` to the backend, or configure a public `VITE_API_BASE_URL` and
appropriate backend CORS policy. The Vite proxy only runs during development.

Activities also displays saved route grades (polling while processing) and the
same **Get new data** action as Grades. Successful sync refreshes the list,
selected summary, grades, and weekly TSS without resetting the selection.
Status polling runs every 30 seconds while idle and every two seconds after
a sync is detected. It also refreshes data when import completes, even if
the original sync request is still pending or has failed to return.

With a development server running and Playwright/Chromium available, run the
mocked browser regression check (no Garmin downloads or weather requests):

```bash
WEB_URL=http://localhost:8001 node tests/activities.browser.cjs
```

Set `PLAYWRIGHT_MODULE` to an existing Playwright module path if it is installed
outside this app. This checks syncing/disabled feedback, refresh, failure,
grade polling/retry, mobile/tablet/desktop overflow, skip-link and Profile
navigation, page titles and focus, and keyboard-operated chart series and data.
