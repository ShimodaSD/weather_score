"""Forward Codex pull-request review events to an Open Bot webhook."""

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


def create_notification(event: dict) -> dict | None:
    """Wrap a submitted Codex review event for the OpenBot monitor."""
    if event.get("repository", {}).get("full_name") != "ShimodaSD/weather_score":
        return None
    if event.get("action") != "submitted" or "comment" in event:
        return None
    if event.get("sender", {}).get("login") != CODEX_LOGIN:
        return None
    if event.get("review", {}).get("user", {}).get("login") != CODEX_LOGIN:
        return None
    number = event.get("pull_request", {}).get("number")
    if type(number) is not int or number <= 0:
        raise ValueError("A positive pull request number is required")
    return {
        "type": "pull_request_review",
        "occurredAt": event["review"].get("submitted_at")
        or datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "data": event,
    }


def send_notification(url: str, payload: dict, secret: str) -> None:
    """POST JSON over HTTPS without following redirects or logging secrets."""
    target = urlsplit(url)
    if (
        target.scheme != "https"
        or not target.hostname
        or target.username
        or target.password
    ):
        raise ValueError("OPENBOT_WEBHOOK_URL must be an HTTPS URL without credentials")
    if target.fragment:
        raise ValueError("OPENBOT_WEBHOOK_URL must not contain a fragment")
    if not secret:
        raise ValueError("OPENBOT_WEBHOOK_SECRET is required")
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    timestamp = str(int(time.time()))
    delivery_id = str(uuid4())
    signed_message = f"{timestamp}.{delivery_id}.".encode() + body
    signature = hmac.new(secret.encode("utf-8"), signed_message, "sha256").hexdigest()
    headers = {
        "Content-Type": "application/json",
        "x-openbot-timestamp": timestamp,
        "x-openbot-delivery-id": delivery_id,
        "x-openbot-signature": signature,
    }
    connection = http.client.HTTPSConnection(target.hostname, target.port, timeout=30)
    path = target.path or "/"
    if target.query:
        path += f"?{target.query}"
    try:
        connection.request("POST", path, body, headers)
        response = connection.getresponse()
        if not 200 <= response.status < 300:
            raise RuntimeError(f"Open Bot webhook returned HTTP {response.status}")
    finally:
        connection.close()


def main() -> int:
    """Read the Actions event and deliver any applicable notification."""
    try:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        payload = create_notification(event)
        if payload is None:
            print("No matching Codex review event to forward.")
            return 0
        url = os.environ.get("OPENBOT_WEBHOOK_URL", "")
        if not url:
            raise ValueError("OPENBOT_WEBHOOK_URL is required")
        send_notification(url, payload, os.environ.get("OPENBOT_WEBHOOK_SECRET", ""))
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        http.client.HTTPException,
        RuntimeError,
    ) as error:
        print(
            f"Open Bot notification failed ({type(error).__name__}). Check event and webhook configuration.",
            file=sys.stderr,
        )
        return 1
    print("Codex review sent to Open Bot.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
