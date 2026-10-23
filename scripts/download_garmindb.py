"""Run GarminDB 3.9 downloads with structured file progress on stdout."""

import json
import runpy
import shutil
from pathlib import Path
from typing import Any


def install_download_progress(download: type) -> None:
    """Instrument the existing downloader without changing its download rules."""
    get_activities = download.get_activities
    get_summaries = download._Download__get_activity_summaries
    save_json = download.save_json_to_file
    save_binary = download.save_binary_file
    pending: set[Path] = set()
    directory = Path()
    replace_existing = False
    total = 0
    downloaded = 0

    def print_progress(phase: str) -> None:
        print("garmin-progress: " + json.dumps({
            "phase": phase, "downloaded_files": downloaded, "total_files": total,
        }), flush=True)

    def record_download(path: Path) -> None:
        nonlocal downloaded
        if path in pending and path.is_file():
            pending.remove(path)
            downloaded += 1
            print_progress("downloading")

    def fetch_summaries(instance: Any, start: int, count: int) -> Any:
        nonlocal total
        activities = get_summaries(instance, start, count)
        if activities is None:
            raise RuntimeError("Garmin did not return an activity list")
        for activity in activities:
            activity_id = str(activity["activityId"])
            summary = directory / f"activity_{activity_id}.json"
            if summary.is_file() and not replace_existing:
                continue
            details = directory / f"activity_details_{activity_id}.json"
            if not summary.is_file():
                pending.add(summary)
            if replace_existing or not details.is_file():
                pending.add(details)
            if replace_existing or not (directory / f"{activity_id}.fit").is_file():
                pending.add(Path(instance.temp_dir) / f"activity_{activity_id}.zip")
        total = len(pending)
        print_progress("downloading")
        return activities

    def save_json_file(instance: Any, filename: str, data: Any,
                       overwrite: bool = False) -> None:
        save_json(filename, data, overwrite)
        record_download(Path(f"{filename}.json"))

    def save_binary_file(instance: Any, filename: str, url: str,
                         overwrite: bool = False) -> None:
        save_binary(instance, filename, url, overwrite)
        record_download(Path(filename))

    def fetch_activities(instance: Any, target: str, count: int,
                         overwrite: bool = False) -> None:
        nonlocal directory, replace_existing, total, downloaded
        directory, replace_existing = Path(target), overwrite
        pending.clear()
        total = downloaded = 0
        get_activities(instance, target, count, overwrite)
        if pending:
            raise RuntimeError(f"{len(pending)} Garmin files were not downloaded")
        print_progress("importing")

    download.get_activities = fetch_activities
    download._Download__get_activity_summaries = fetch_summaries
    download.save_json_to_file = save_json_file
    download.save_binary_file = save_binary_file


def main() -> None:
    """Add file counters to the installed GarminDB CLI in this subprocess."""
    import garmindb

    install_download_progress(garmindb.Download)
    executable = shutil.which("garmindb_cli.py")
    if executable is None:
        raise SystemExit("GarminDB CLI is not installed")
    runpy.run_path(executable, run_name="__main__")


if __name__ == "__main__":
    main()
