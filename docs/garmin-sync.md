# GarminDB sync

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
