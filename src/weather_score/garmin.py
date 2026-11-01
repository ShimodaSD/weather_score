"""Download activity files using the Garmin Connect Personal API."""

import io
import json
import os
import time
import zipfile
from pathlib import Path

import requests

BASE_URL = "https://personal.connectapi.garmin.com"
TOKEN_PATH = "/personalapitoken-service/personal-api/personal-api-key/token"
SEARCH_PATH = "/activitylist-service/activities/search/activities"
PAGE_SIZE = 99
ACTIVITY_CACHE_SECONDS = 300


def fetch_activities(directory: Path, count: int) -> None:
    """Download missing summaries, details and FIT files within the sync window."""
    key = os.environ.get("GARMIN_CONNECT", "").strip()
    if not key:
        raise ValueError("set GARMIN_CONNECT to a Garmin Personal API key")
    if not key.isascii() or any(character.isspace() for character in key):
        raise ValueError("GARMIN_CONNECT must be an API key without whitespace")
    if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
        raise ValueError("activity download count must be a positive integer")
    directory.mkdir(parents=True, exist_ok=True)
    cache = directory / ".activity-list.json"
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
                except (TypeError, ValueError):
                    delay = 0
                if 0 < delay <= 60:
                    time.sleep(delay)
                    response = session.request(
                        method, BASE_URL + path, timeout=30,
                        allow_redirects=False, **kwargs
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
        if (
            cache.is_file()
            and time.time() - cache.stat().st_mtime < ACTIVITY_CACHE_SECONDS
        ):
            try:
                cached = json.loads(cache.read_text())
                if isinstance(cached, list) and len(cached) >= count:
                    activities = cached[:count]
            except (OSError, json.JSONDecodeError):
                pass
        seen = set()
        while not activities and len(activities) < count:
            limit = min(PAGE_SIZE, count - len(activities))
            page = fetch_response(
                "GET",
                SEARCH_PATH,
                params={
                    "start": len(activities),
                    "limit": limit,
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
        if activities:
            cache.write_text(json.dumps(activities))

        jobs = []
        for activity in activities:
            activity_id = activity["activityId"]
            for filename, kind in (
                (f"activity_{activity_id}.json", "summary"),
                (f"activity_details_{activity_id}.json", "details"),
                (f"{activity_id}.fit", "fit"),
            ):
                if not (directory / filename).is_file():
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
                if len(content) < 12 or content[8:12] != b".FIT":
                    raise ValueError("Garmin archive contains invalid FIT data")
            target = directory / filename
            temporary = target.with_suffix(target.suffix + ".part")
            try:
                temporary.write_bytes(content)
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
            print_progress("downloading", downloaded)
        print_progress("importing", len(jobs))
