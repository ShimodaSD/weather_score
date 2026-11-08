"""Download activity files using the Garmin Connect Personal API."""

import calendar
import hashlib
import io
import json
import os
import time
import zipfile
from datetime import date, datetime
from pathlib import Path

import requests

from .fit_integrity import validate_fit

BASE_URL = "https://personal.connectapi.garmin.com"
TOKEN_PATH = "/personalapitoken-service/personal-api/personal-api-key/token"
SEARCH_PATH = "/activitylist-service/activities/search/activities"
PAGE_SIZE = 99


def fetch_activities(directory: Path, *, refresh_changed: bool = False) -> None:
    """Download missing summaries, details and FIT files within the sync window."""
    key = os.environ.get("GARMIN_CONNECT", "").strip()
    if not key:
        raise ValueError("set GARMIN_CONNECT to a Garmin Personal API key")
    if not key.isascii() or any(character.isspace() for character in key):
        raise ValueError("GARMIN_CONNECT must be an API key without whitespace")
    directory.mkdir(parents=True, exist_ok=True)
    today = datetime.now().astimezone().date()
    year, month = divmod(today.year * 12 + today.month - 4, 12)
    month += 1
    start_date = date(year, month, min(today.day, calendar.monthrange(year, month)[1]))
    with requests.Session() as session:

        def fetch_response(
            method: str, path: str, **kwargs: object
        ) -> requests.Response:
            response = session.request(
                method, BASE_URL + path, timeout=30, allow_redirects=False, **kwargs
            )
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "")
                try:
                    delay = float(retry_after)
                except TypeError, ValueError:
                    delay = 0
                if 0 < delay <= 60:
                    time.sleep(delay)
                    response = session.request(
                        method,
                        BASE_URL + path,
                        timeout=30,
                        allow_redirects=False,
                        **kwargs,
                    )
            if response.status_code != 200:
                raise ValueError(f"Garmin {method} {path}: HTTP {response.status_code}")
            return response

        token = fetch_response(
            "POST",
            TOKEN_PATH,
            headers={
                "Authorization": f"ApiKey {key}",
                "Accept": "*/*",
            },
        ).text.strip()
        if not token or any(character.isspace() for character in token):
            raise ValueError("Garmin returned an invalid access token")
        session.headers.update(
            {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        )
        activities = []
        seen = set()
        while True:
            limit = PAGE_SIZE
            page = fetch_response(
                "GET",
                SEARCH_PATH,
                params={
                    "start": len(activities),
                    "limit": limit,
                    "startDate": start_date.isoformat(),
                    "endDate": today.isoformat(),
                },
            ).json()
            if not isinstance(page, list) or len(page) > limit:
                raise ValueError("Garmin returned an invalid activity list")
            for activity in page:
                activity_id = (
                    activity.get("activityId") if isinstance(activity, dict) else None
                )
                if (
                    not isinstance(activity_id, int)
                    or isinstance(activity_id, bool)
                    or activity_id <= 0
                    or activity_id in seen
                ):
                    raise ValueError(
                        "Garmin returned an invalid or repeated activity identifier"
                    )
                seen.add(activity_id)
                activities.append(activity)
            if len(page) < limit:
                break

        jobs = []
        for activity in activities:
            activity_id = activity["activityId"]
            summary_path = directory / f"activity_{activity_id}.json"
            changed = refresh_changed and not summary_path.is_file()
            if refresh_changed and summary_path.exists():
                try:
                    changed = json.loads(summary_path.read_text()) != activity
                except json.JSONDecodeError:
                    changed = True
            files = (
                (f"activity_{activity_id}.json", "summary"),
                (f"activity_details_{activity_id}.json", "details"),
                (f"{activity_id}.fit", "fit"),
            )
            if refresh_changed:
                files = files[1:] + files[:1]
            for filename, kind in files:
                if changed or not (directory / filename).is_file():
                    jobs.append((activity, filename, kind))

        def print_progress(phase: str, downloaded: int) -> None:
            print(
                "garmin-progress: "
                + json.dumps(
                    {
                        "phase": phase,
                        "downloaded_files": downloaded,
                        "total_files": len(jobs),
                    }
                ),
                flush=True,
            )

        print_progress("downloading", 0)
        for downloaded, (activity, filename, kind) in enumerate(jobs, 1):
            activity_id = activity["activityId"]
            if kind == "summary":
                content = json.dumps(activity).encode()
            elif kind == "details":
                details = fetch_response(
                    "GET", f"/activity-service/activity/{activity_id}"
                ).json()
                if (
                    not isinstance(details, dict)
                    or details.get("activityId") != activity_id
                ):
                    raise ValueError("Garmin returned invalid activity details")
                content = json.dumps(details).encode()
            else:
                response = fetch_response(
                    "GET",
                    f"/download-service/files/activity/{activity_id}",
                    headers={"Accept": "application/x-zip-compressed"},
                )
                with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                    files = [
                        item
                        for item in archive.infolist()
                        if item.filename.lower().endswith(".fit")
                    ]
                    if (
                        len(files) != 1
                        or not 0 < files[0].file_size <= 128 * 1024 * 1024
                    ):
                        raise ValueError(
                            "Garmin archive must contain one FIT file of at most 128 MiB"
                        )
                    content = archive.read(files[0])
                validate_fit(content)
            target = directory / filename
            if refresh_changed and target.is_file():
                previous = target.read_bytes()
                digest = hashlib.sha256(previous).hexdigest()
                versions_root = directory / ".versions"
                versions_root.mkdir(mode=0o700, exist_ok=True)
                versions = versions_root / filename
                versions.mkdir(mode=0o700, exist_ok=True)
                archive = versions / digest
                try:
                    with os.fdopen(
                        os.open(archive, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600),
                        "wb",
                    ) as saved:
                        saved.write(previous)
                except FileExistsError:
                    if hashlib.sha256(archive.read_bytes()).hexdigest() != digest:
                        raise ValueError(
                            "Existing activity version failed integrity check"
                        )
            temporary = target.with_suffix(target.suffix + ".part")
            try:
                temporary.write_bytes(content)
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
            print_progress("downloading", downloaded)
        print_progress("importing", len(jobs))
