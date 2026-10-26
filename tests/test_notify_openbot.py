"""Checks for the review notification bridge without external requests."""

import hashlib
import hmac
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from scripts.notify_openbot import (
    CODEX_LOGIN,
    create_notification,
    main,
    send_notification,
)


@pytest.fixture
def review_event():
    return {
        "action": "submitted",
        "sender": {"login": CODEX_LOGIN},
        "repository": {"full_name": "ShimodaSD/weather_score"},
        "pull_request": {"number": 42, "title": "Fix weather"},
        "review": {
            "user": {"login": CODEX_LOGIN},
            "body": "Review finding",
            "submitted_at": "2026-10-22T18:30:00Z",
            "html_url": "https://github.com/owner/repo/pull/42#review-1",
        },
    }


def test_create_review_notification(review_event):
    assert create_notification(review_event) == {
        "type": "pull_request_review",
        "occurredAt": "2026-10-22T18:30:00Z",
        "data": review_event,
    }


@pytest.mark.parametrize("state", ["open", "closed"])
def test_notify_new_commits_on_open_pr(review_event, state):
    event = review_event
    event["action"] = "synchronize"
    event["sender"]["login"] = "contributor"
    del event["review"]
    event["pull_request"].update(state=state, updated_at="2026-10-26T12:00:00Z")
    event.update(before="old-sha", after="new-sha")
    notification = create_notification(event)
    if state == "closed":
        assert notification is None
    else:
        assert notification == {
            "type": "pull_request",
            "occurredAt": "2026-10-26T12:00:00Z",
            "data": event,
        }


@pytest.mark.parametrize("body", [None, "", "  "])
def test_forward_reviews_without_findings(review_event, body):
    review_event["review"]["body"] = body
    assert create_notification(review_event)["data"] == review_event


@pytest.mark.parametrize(
    "field", ["sender", "author", "repository", "action", "comment"]
)
def test_skip_unrelated_events(review_event, field):
    if field == "sender":
        review_event["sender"]["login"] = "someone"
    elif field == "author":
        review_event["review"]["user"]["login"] = "someone"
    elif field == "repository":
        review_event["repository"]["full_name"] = "someone/fork"
    elif field == "comment":
        review_event["comment"] = review_event.pop("review")
    else:
        review_event["action"] = "dismissed"
    assert create_notification(review_event) is None


@pytest.mark.parametrize("number", [None, 0, -1, "42", True])
def test_reject_invalid_pull_request_number(review_event, number):
    review_event["pull_request"]["number"] = number
    with pytest.raises(ValueError, match="pull request number"):
        create_notification(review_event)


@pytest.mark.parametrize("status", [200, 202, 204, 302, 400, 500])
def test_send_notification(status, review_event):
    payload = create_notification(review_event)
    connection = MagicMock()
    connection.getresponse.return_value.status = status
    with patch(
        "scripts.notify_openbot.http.client.HTTPSConnection", return_value=connection
    ) as connect:
        if status in (200, 202):
            send_notification("https://bot.example/hook?key=value", payload, "secret")
        else:
            with pytest.raises(RuntimeError, match=f"HTTP {status}"):
                send_notification(
                    "https://bot.example/hook?key=value", payload, "secret"
                )
    connect.assert_called_once_with("bot.example", None, timeout=30)
    args = connection.request.call_args.args
    assert args[:2] == ("POST", "/hook?key=value")
    body = connection.request.call_args.kwargs["body"]
    assert json.loads(body) == payload
    headers = connection.request.call_args.kwargs["headers"]
    signed_message = (
        headers["x-openbot-timestamp"].encode()
        + b"."
        + headers["x-openbot-delivery-id"].encode()
        + b"."
        + body
    )
    assert (
        headers["x-openbot-signature"]
        == "sha256=" + hmac.new(b"secret", signed_message, hashlib.sha256).hexdigest()
    )
    assert "Authorization" not in headers
    connection.close.assert_called_once()


@pytest.mark.parametrize(
    "url",
    [
        "",
        "http://bot.example",
        "https://user:pass@bot.example",
        "https://bot.example/#fragment",
    ],
)
def test_reject_invalid_webhook(url):
    with pytest.raises(ValueError):
        send_notification(url, {"type": "pull_request_review"}, "secret")


def test_main_delivers_event(review_event, tmp_path, monkeypatch):
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(review_event))
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
    monkeypatch.setenv("OPENBOT_WEBHOOK_URL", "https://bot.example/hook")
    monkeypatch.setenv("OPENBOT_WEBHOOK_SECRET", "secret")
    with patch("scripts.notify_openbot.send_notification") as send:
        assert main() == 0
    send.assert_called_once_with(
        url="https://bot.example/hook",
        payload=create_notification(review_event),
        secret="secret",
    )


def test_main_failure_hides_secrets(review_event, tmp_path, monkeypatch, capsys):
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(review_event))
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
    monkeypatch.setenv("OPENBOT_WEBHOOK_URL", "https://bot.example/private-token")
    monkeypatch.setenv("OPENBOT_WEBHOOK_SECRET", "secret")
    with patch(
        "scripts.notify_openbot.send_notification", side_effect=OSError("private-token")
    ):
        assert main() == 1
    assert "private-token" not in capsys.readouterr().err


def test_require_signing_secret():
    with (
        patch("scripts.notify_openbot.http.client.HTTPSConnection") as connect,
        pytest.raises(ValueError, match="OPENBOT_WEBHOOK_SECRET"),
    ):
        send_notification("https://bot.example/hook", {}, "")
    connect.assert_not_called()


def test_create_notification_without_submission_time(review_event):
    del review_event["review"]["submitted_at"]
    occurred_at = create_notification(review_event)["occurredAt"]
    assert occurred_at.endswith("Z")
    assert datetime.fromisoformat(occurred_at).utcoffset().total_seconds() == 0


def test_sign_exact_utf8_body():
    connection = MagicMock()
    connection.getresponse.return_value.status = 202
    with (
        patch(
            "scripts.notify_openbot.http.client.HTTPSConnection",
            return_value=connection,
        ),
        patch("scripts.notify_openbot.time.time", return_value=1792693800),
        patch("scripts.notify_openbot.uuid4", return_value="delivery-123"),
    ):
        send_notification("https://bot.example/hook", {"title": "São Paulo"}, "secret")
    body = connection.request.call_args.kwargs["body"]
    headers = connection.request.call_args.kwargs["headers"]
    assert body == '{"title":"São Paulo"}'.encode()
    assert headers["x-openbot-timestamp"] == "1792693800"
    assert headers["x-openbot-delivery-id"] == "delivery-123"
    assert (
        headers["x-openbot-signature"]
        == "sha256="
        + hmac.new(
            b"secret", b"1792693800.delivery-123." + body, hashlib.sha256
        ).hexdigest()
    )


@pytest.mark.parametrize("size", [64 * 1024, 64 * 1024 + 1])
def test_enforce_body_byte_limit(size):
    payload = {"data": "é" * ((size - 12) // 2)}
    payload["data"] += "x" * (
        size
        - len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode())
    )
    connection = MagicMock()
    connection.getresponse.return_value.status = 202
    with patch(
        "scripts.notify_openbot.http.client.HTTPSConnection", return_value=connection
    ) as connect:
        if size == 64 * 1024:
            send_notification("https://bot.example/hook", payload, "secret")
            assert len(connection.request.call_args.kwargs["body"]) == size
        else:
            with pytest.raises(ValueError, match="64 KiB"):
                send_notification("https://bot.example/hook", payload, "secret")
            connect.assert_not_called()
