.PHONY: garmin-sync postgres-init

postgres-init:
	uv run $(if $(wildcard .env),--env-file .env) python scripts/initialize_postgres.py

garmin-sync:
	uv run $(if $(wildcard .env),--env-file .env) --extra garmin python scripts/sync_garmindb.py
