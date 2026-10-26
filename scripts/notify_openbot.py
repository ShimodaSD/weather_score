"""Forward Codex pull-request reviews to an OpenBot webhook."""

import hmac
import http.client
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

CODEX_LOGIN = "chatgpt-codex-connector[bot]"
REPOSITORY = "ShimodaSD/weather_score"
WEBHOOK_TIMEOUT = 30


def create_notification(event: dict) -> dict | None:
    """Create a notification from a submitted Codex review."""

    if event.get("repository", {}).get("full_name") != REPOSITORY:
        print("Skipping event: repository does not match.")
        return None

    if event.get("action") != "submitted":
        print("Skipping event: not a submitted review.")
        return None

    if "comment" in event:
        print("Skipping event: comment event.")
        return None

    sender = event.get("sender", {}).get("login")
    reviewer = event.get("review", {}).get("user", {}).get("login")

    if sender != CODEX_LOGIN or reviewer != CODEX_LOGIN:
        print("Skipping event: review was not submitted by the Codex bot.")
        return None

    pr_number = event.get("pull_request", {}).get("number")

    if type(pr_number) is not int or pr_number <= 0:
        raise ValueError("A valid pull request number is required.")

    print(f"Processing Codex review for PR #{pr_number}")

    return {
        "type": "pull_request_review",
        "occurredAt": (
            event["review"].get("submitted_at")
            or datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        ),
        "data": event,
    }


def send_notification(
    url: str,
    payload: dict,
    secret: str,
) -> None:
    """Send a signed HTTPS notification to OpenBot."""

    target = urlsplit(url)

    if (
        target.scheme != "https"
        or not target.hostname
        or target.username
        or target.password
        or target.fragment
    ):
        raise ValueError(
            "OPENBOT_WEBHOOK_URL must be a valid HTTPS URL "
            "without credentials or fragments."
        )

    if not secret:
        raise ValueError("OPENBOT_WEBHOOK_SECRET is missing or empty.")

    body = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    if len(body) > 64 * 1024:
        raise ValueError("OpenBot webhook body exceeds 64 KiB.")

    timestamp = str(int(time.time()))
    delivery_id = str(uuid4())

    signed_message = f"{timestamp}.{delivery_id}.".encode() + body

    signature = hmac.new(
        secret.encode("utf-8"),
        signed_message,
        "sha256",
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "weather-score-codex-review/1.0",
        "x-openbot-timestamp": timestamp,
        "x-openbot-delivery-id": delivery_id,
        "x-openbot-signature": f"sha256={signature}",
    }

    path = target.path or "/"

    if target.query:
        path += f"?{target.query}"

    connection = http.client.HTTPSConnection(
        target.hostname,
        target.port,
        timeout=WEBHOOK_TIMEOUT,
    )

    print("Sending Codex review notification to OpenBot...")

    try:
        connection.request(
            "POST",
            path,
            body=body,
            headers=headers,
        )

        response = connection.getresponse()
        status = response.status
        response.read(4096)

        print(f"OpenBot HTTP status: {status}")

        if status not in (200, 202):
            raise RuntimeError(
                f"OpenBot webhook returned HTTP {status} ({response.reason})"
            )

        print("OpenBot notification delivered successfully.")

    finally:
        connection.close()


def main() -> int:
    """Read GitHub Actions event and notify OpenBot."""

    print("Starting Codex review notification workflow...")

    try:
        event_path = os.environ.get("GITHUB_EVENT_PATH")

        if not event_path:
            raise ValueError("GITHUB_EVENT_PATH environment variable is missing.")

        event = json.loads(Path(event_path).read_text(encoding="utf-8"))

        payload = create_notification(event)

        if payload is None:
            print("No matching Codex review event to forward.")
            return 0

        webhook_url = os.environ.get("OPENBOT_WEBHOOK_URL", "")
        webhook_secret = os.environ.get("OPENBOT_WEBHOOK_SECRET", "")

        if not webhook_url:
            raise ValueError("OPENBOT_WEBHOOK_URL GitHub secret is missing.")

        if not webhook_secret:
            raise ValueError("OPENBOT_WEBHOOK_SECRET GitHub secret is missing.")

        send_notification(
            url=webhook_url,
            payload=payload,
            secret=webhook_secret,
        )

    except (
        TimeoutError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
        http.client.HTTPException,
        RuntimeError,
    ) as error:
        print(
            f"Open Bot notification failed: {type(error).__name__}",
            file=sys.stderr,
        )
        return 1

    print("Codex review successfully forwarded to OpenBot.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
