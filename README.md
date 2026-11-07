# Wind Score

Run from the project root with Docker Compose:

```bash
docker compose up -d
```

Create `.env` from `.env.example` and fill in the weather API key and
application authentication settings first. The default configuration also
requires the private `.env.supabase` and Supabase CA certificate described in
[Supabase database](docs/supabase.md). The frontend is at http://localhost:8001
and the API at http://localhost:8002.

Local working files stay under the ignored `workspace/` directory:
local PostgreSQL data in `workspace/postgres`, container dependencies in
`workspace/docker`, and Garmin files in `workspace/garmin`. The Supabase
database is remote; local PostgreSQL is a separate, unsynchronized copy.

For Garmin setup and the data refresh command, see [Garmin sync](docs/garmin-sync.md).
