.PHONY: garmin-sync

garmin-sync:
	uv run $(if $(wildcard .env),--env-file .env) --extra garmin python scripts/sync_garmindb.py
