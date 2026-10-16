# Wind Score

Run from the project root with Docker Compose:

```bash
docker compose up -d
```

Create `.env` from `.env.example` and fill in the database password, database
names, weather API key, and application authentication settings first.
Compose reads only this project's `.env` and overrides the database host and
port to use its PostgreSQL service. The frontend is at http://localhost:8001
and the API at http://localhost:8002.

All persistent files stay under the ignored `workspace/` directory:
PostgreSQL data in `workspace/postgres`, container dependencies in
`workspace/docker`, and Garmin files in `workspace/garmin`. PostgreSQL starts
empty; it does not read or migrate an existing host database.

For Garmin setup and the data refresh command, see [Garmin sync](docs/garmin-sync.md).
