"""Restore a Garmin activity archive and import it into the configured databases."""

import argparse
import filecmp
import os
import shutil
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

from sync_garmindb import (
    _bootstrap_database,
    _get_garmin_config,
    _import_postgres,
    _prepare_postgres_database,
    _run_garmindb,
    _sync_postgres_activity_names,
    _sync_postgres_activity_tss,
    _validate_database,
)


def restore_archive(archive: Path, destination: Path) -> int:
    """Restore flat activity files without overwriting different existing files."""
    with tempfile.TemporaryDirectory(prefix="garmin-archive-") as temporary:
        staging = Path(temporary)
        names: set[str] = set()
        with tarfile.open(archive, "r:gz") as source:
            for member in source:
                path = PurePosixPath(member.name)
                if member.isdir() and path.parts == ("Activities",):
                    continue
                if member.isfile() and path.parts == ("Activities", ".activity-list.json"):
                    continue
                if not member.isfile() or len(path.parts) != 2 or path.parts[0] != "Activities" or path.name in {"", ".", ".."} or path.name in names:
                    raise ValueError("Archive must contain only unique files directly inside Activities.")
                names.add(path.name)
                incoming = source.extractfile(member)
                if incoming is None:
                    raise ValueError("Cannot read archive member.")
                with incoming, (staging / path.name).open("xb") as output:
                    shutil.copyfileobj(incoming, output)
        if not names:
            raise ValueError("Archive contains no activity files.")
        destination.mkdir(parents=True, exist_ok=True)
        for name in names:
            existing = destination / name
            if existing.exists() and (not existing.is_file() or not filecmp.cmp(staging / name, existing, shallow=False)):
                raise FileExistsError(f"Existing activity file differs: {name}")
        for name in names:
            target = destination / name
            if not target.exists():
                shutil.copyfile(staging / name, target)
        return len(names)


def main() -> None:
    """Import a compressed archive using the existing GarminDB pipeline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Path to an Activities tar.gz archive")
    args = parser.parse_args()
    configured_target = os.environ.get("GARMINDB_PATH")
    database = os.environ.get("DB_NAME_GARMIN")
    if not configured_target or not database:
        parser.error("GARMINDB_PATH and DB_NAME_GARMIN must be configured")
    target = Path(configured_target).expanduser().resolve()
    if target.name != "garmin_activities.db":
        parser.error("GARMINDB_PATH must end with garmin_activities.db")
    data_directory, config = _get_garmin_config(target)
    count = restore_archive(args.archive, data_directory / "FitFiles" / "Activities")
    _bootstrap_database(target, None)
    _prepare_postgres_database(database)
    _run_garmindb(data_directory.parent, ["--config", str(target.parent / "config"), "--activities", "--import"])
    if not _validate_database(target, "activities"):
        raise SystemExit("GarminDB did not create a valid activities database")
    _import_postgres(config, data_directory.parent, database, True)
    _sync_postgres_activity_names(target, database)
    scored, excluded = _sync_postgres_activity_tss(database)
    print(f"Imported archive with {count} files; TSS calculated for {scored} activities, {excluded} unavailable.")


if __name__ == "__main__":
    main()
