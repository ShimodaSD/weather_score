#!/bin/sh
set -eu

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set ON_ERROR_STOP=1 \
    --set garmin_db="$DB_NAME_GARMIN" <<'SQL'
SELECT format('CREATE DATABASE %I', :'garmin_db')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'garmin_db')\gexec
SQL
