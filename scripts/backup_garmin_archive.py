"""Compress downloaded Garmin activity files into a configured archive."""

import os
import tarfile
import tempfile
from pathlib import Path

from dotenv import load_dotenv


def backup_activities(source: Path, destination: Path) -> int:
    """Write a private archive without replacing an existing backup."""
    if not source.is_dir():
        raise ValueError(f"Activity directory does not exist: {source}")
    files = sorted(path for path in source.iterdir() if path.is_file() and not path.is_symlink() and not path.name.startswith("."))
    if not files:
        raise ValueError("Activity directory contains no files.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".garmin-backup-", dir=destination.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as output, tarfile.open(fileobj=output, mode="w:gz") as archive:
            for path in files:
                archive.add(path, arcname=f"Activities/{path.name}", recursive=False)
        os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return len(files)


def main() -> None:
    """Read paths from the root environment and create a compressed backup."""
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    source = os.environ.get("GARMIN_BACKUP_SOURCE", "").strip()
    backup = os.environ.get("GARMIN_BACKUP_PATH", "").strip()
    if not source or not backup:
        raise SystemExit("Set GARMIN_BACKUP_SOURCE and GARMIN_BACKUP_PATH in .env.")
    destination = Path(backup).expanduser().resolve()
    if not destination.name.endswith(".tar.gz"):
        raise SystemExit("GARMIN_BACKUP_PATH must end with .tar.gz.")
    try:
        count = backup_activities(Path(source).expanduser().resolve(), destination)
    except (OSError, ValueError, tarfile.TarError) as error:
        raise SystemExit(f"Garmin backup failed: {error}") from error
    print(f"Saved {count} activity files to {destination}.")


if __name__ == "__main__":
    main()
