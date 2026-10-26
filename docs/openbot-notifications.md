# Codex review notifications

The existing `.github/workflows/main.yml` runs `scripts/notify_openbot.py`
when `chatgpt-codex-connector[bot]` submits a PR review in
`ShimodaSD/weather_score`. Inline comment events do not trigger delivery;
the monitor fetches reviews and inline comments from GitHub. Blank review
bodies are accepted.

The request body wraps the complete GitHub event:

```json
{
  "type": "pull_request_review",
  "occurredAt": "2026-10-22T18:30:00Z",
  "data": {
    "action": "submitted",
    "repository": {"full_name": "ShimodaSD/weather_score"},
    "pull_request": {"number": 42}
  }
}
```

The example shows only the identifying fields; the script preserves all event
fields under `data` without generating a findings summary.

In repository Settings → Secrets and variables → Actions, configure
`OPENBOT_WEBHOOK_URL` with the HTTPS endpoint and `OPENBOT_WEBHOOK_SECRET`
with the shared secret. URLs and credentials are not logged.

`OPENBOT_WEBHOOK_SECRET` is required and must match the routine's signing
secret. Authentication uses these headers:

- `x-openbot-timestamp`: current Unix timestamp in seconds.
- `x-openbot-delivery-id`: a new UUID for each delivery attempt.
- `x-openbot-signature`: `sha256=` followed by lowercase hexadecimal HMAC-SHA256.

The signed message is the UTF-8 timestamp, a dot, the delivery ID, another dot,
and the exact JSON body bytes sent over HTTPS. The body is serialized once;
no bearer token is sent. `occurredAt` uses the review's `submitted_at` UTC time,
falling back to the current UTC time if absent. The signature timestamp always
uses the delivery time so reruns do not reuse an old timestamp.

Merge the script into the default branch before testing: the workflow checks
out that trusted branch rather than PR code. No Python dependencies are needed.
A response other than 200 or 202, or a network failure, fails the action. UTF-8
request bodies over 64 KiB are rejected before sending. Requests time out after
30 seconds and redirects are rejected. Failed deliveries can be retried by
rerunning the workflow; reruns can produce repeat messages.

This follows the [OpenBot webhook contract](https://github.com/nightly-labs/openbot/blob/main/docs/webhooks.md).
The host clock must be within five minutes of the sender. HTTP 202 acknowledges
receipt, not completion of the routine. The script does not automatically retry;
each workflow rerun creates a new delivery ID rather than deduplicating the event.

GitHub withholds repository secrets for review workflows from fork PRs, so
this workflow cannot deliver those notifications with its current triggers.
See [GitHub review event documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request_review).
Review text and PR metadata leave GitHub for the configured webhook service.
