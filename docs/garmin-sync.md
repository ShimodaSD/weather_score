# GarminDB sync

## Docker Compose

Compose uses the repository-root `.env`, its own PostgreSQL service, and Garmin
files inside this project. It does not mount your host home directory.

Place your complete `GarminConnectConfig.json` in the project root, with your
Garmin username in `credentials.user` and SQLite as the database type. Set
`SECRET_GARMIN` in `.env` to your Garmin password. Each sync generates
`workspace/garmin/.GarminDb/GarminConnectConfig.json` from that file, injecting
the password and project data path. The generated file has mode `0600`;
both config files and `.env` are ignored by Git. Existing password-file and
secure-password settings are replaced by the `.env` password. Existing session
files can also be placed in `workspace/garmin/.GarminDb/`.

Place any existing downloaded Garmin data and SQLite databases in
`workspace/garmin/HealthData/` (the activities database belongs at
`HealthData/DBs/garmin_activities.db`). If starting fresh, GarminDB downloads data
using the start dates in your configuration. These directories are ignored by Git.

```bash
docker compose up -d
docker compose exec -w /app backend make garmin-sync
```

Compose supplies the container database path and mounts the project Garmin
configuration at `/root/.GarminDb`. It disables the optional bootstrap path;
reuse existing data by placing it in the project directory above. Subsequent
refreshes use the same command or the dashboard's **Get new data** button.
The first sync populates the new PostgreSQL database before activity pages can
load. Merely starting Compose does not download Garmin data.

## Running without Docker

The project keeps Garmin credentials and session files in GarminDB's standard
`~/.GarminDb` directory. Install no separate GarminDB checkout or duplicate
configuration.

In `~/.GarminDb/GarminConnectConfig.json`, use SQLite and set the data directory.
For example, this stores data below `/Users/me/dbs/garmindb/HealthData`:

```json
{
  "db": {"type": "sqlite"},
  "directories": {"relative_to_home": false, "base_dir": "HealthData"}
}
```

Run the command from `/Users/me/dbs/garmindb`, or let the project command do so
by setting the matching database path:

```bash
export GARMINDB_PATH=/Users/me/dbs/garmindb/HealthData/DBs/garmin_activities.db
export DB_NAME_GARMIN=garmin
```

The command also loads these values from a repository-root `.env` file when it
exists.

For the initial bootstrap, point at an existing valid activities database. The
command copies that database so its activity history is reused:

```bash
GARMINDB_BOOTSTRAP_PATH=/Users/me/old/HealthData/DBs/garmin_activities.db make garmin-sync
```

If no existing databases are available, omit `GARMINDB_BOOTSTRAP_PATH`; the first
run starts from the dates in the GarminDB config. Every later refresh is the same
command:

```bash
make garmin-sync
```

The command downloads activities only, keeps the local SQLite database, and
imports every locally downloaded Garmin data type into `DB_NAME_GARMIN` on the
same PostgreSQL server as `DB_NAME`. GarminDB creates separate `garmin`,
`garmin_activities`, and `garmin_monitoring` schemas. The first PostgreSQL import
processes all local files; later runs import only files from the latest overlap.
After import, the command copies activity names from SQLite into PostgreSQL to
work around GarminDB 3.9 passing numeric JSON IDs to its text primary key.
