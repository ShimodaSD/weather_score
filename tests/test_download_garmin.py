import io
import json
import os
import zipfile
from unittest.mock import MagicMock

import pytest
import requests
from weather_score import garmin


def create_archive(filename="record.fit", content=b"\x00" * 8 + b".FIT"):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(filename, content)
    return output.getvalue()


@pytest.fixture
def session(monkeypatch):
    monkeypatch.setenv("GARMIN_CONNECT", "private-key")
    session = MagicMock()
    session.__enter__.return_value = session
    monkeypatch.setattr(garmin.requests, "Session", lambda: session)
    return session


def create_response(data=None, *, text="bearer-token", content=b"", status=200):
    response = MagicMock(status_code=status, text=text, content=content)
    response.json.return_value = data
    return response


def test_download_paginates_saves_files_and_reuses_existing_files(
    tmp_path, session, monkeypatch, capsys
):
    monkeypatch.setattr(garmin, "PAGE_SIZE", 1)
    session.request.side_effect = [
        create_response(),
        create_response([{"activityId": 1}]),
        create_response([{"activityId": 2}]),
        create_response([]),
        create_response({"activityId": 1}),
        create_response(content=create_archive()),
        create_response({"activityId": 2}),
        create_response(content=create_archive()),
    ]
    garmin.fetch_activities(tmp_path, 3)
    assert json.loads((tmp_path / "activity_1.json").read_text()) == {"activityId": 1}
    assert (tmp_path / "1.fit").read_bytes()[8:12] == b".FIT"
    assert (
        session.headers.update.call_args.args[0]["Authorization"]
        == "Bearer bearer-token"
    )
    calls = session.request.call_args_list
    assert calls[0].kwargs["headers"] == {
        "Authorization": "ApiKey private-key",
        "Accept": "*/*",
    }
    assert [call.kwargs["params"]["start"] for call in calls[1:4]] == [0, 1, 2]
    assert all(
        call.kwargs["timeout"] == 30 and not call.kwargs["allow_redirects"]
        for call in calls
    )
    progress = [
        json.loads(line.split(": ", 1)[1])
        for line in capsys.readouterr().out.splitlines()
    ]
    assert progress[0] == {
        "phase": "downloading",
        "downloaded_files": 0,
        "total_files": 6,
    }
    assert progress[-1] == {
        "phase": "importing",
        "downloaded_files": 6,
        "total_files": 6,
    }
    session.request.reset_mock(side_effect=True)
    session.request.side_effect = [
        create_response(),
        create_response([{"activityId": 1}]),
    ]
    garmin.fetch_activities(tmp_path, 1)
    assert session.request.call_count == 2
    (tmp_path / "1.fit").unlink()
    session.request.side_effect = [
        create_response(),
        create_response([{"activityId": 1}]),
        create_response(content=create_archive()),
    ]
    garmin.fetch_activities(tmp_path, 1)
    assert (tmp_path / "1.fit").is_file()


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_http_failures_preserve_files_without_leaking_credentials(
    tmp_path, session, status
):
    (tmp_path / "existing.fit").write_bytes(b"existing")
    session.request.return_value = create_response(status=status, text="private-key")
    with pytest.raises(ValueError, match=f"HTTP {status}") as error:
        garmin.fetch_activities(tmp_path, 1)
    assert "private-key" not in str(error.value)
    assert (tmp_path / "existing.fit").read_bytes() == b"existing"
    assert session.request.call_count == 1


@pytest.mark.parametrize(
    "page",
    [
        None,
        {},
        [None],
        [{"activityId": 0}],
        [{"activityId": "../escape"}],
        [{"activityId": True}],
    ],
)
def test_invalid_lists_are_rejected(tmp_path, session, page):
    session.request.side_effect = [create_response(), create_response(page)]
    with pytest.raises(ValueError, match="invalid"):
        garmin.fetch_activities(tmp_path, 1)
    assert not list(tmp_path.iterdir())


def test_repeated_pages_fail_instead_of_looping(tmp_path, session, monkeypatch):
    monkeypatch.setattr(garmin, "PAGE_SIZE", 1)
    session.request.side_effect = [
        create_response(),
        create_response([{"activityId": 1}]),
        create_response([{"activityId": 1}]),
    ]
    with pytest.raises(ValueError, match="repeated"):
        garmin.fetch_activities(tmp_path, 2)


@pytest.mark.parametrize(
    "content",
    [
        b"not a zip",
        create_archive(content=b"invalid"),
        create_archive(filename="record.txt"),
    ],
)
def test_invalid_downloads_do_not_leave_a_completed_fit(tmp_path, session, content):
    session.request.side_effect = [
        create_response(),
        create_response([{"activityId": 1}]),
        create_response({"activityId": 1}),
        create_response(content=content),
    ]
    with pytest.raises((ValueError, zipfile.BadZipFile)):
        garmin.fetch_activities(tmp_path, 1)
    assert not (tmp_path / "1.fit").exists()
    assert not list(tmp_path.glob("*.part"))


def test_archive_paths_cannot_escape_directory(tmp_path, session):
    session.request.side_effect = [
        create_response(),
        create_response([{"activityId": 1}]),
        create_response({"activityId": 1}),
        create_response(content=create_archive("../../escape.fit")),
    ]
    garmin.fetch_activities(tmp_path, 1)
    assert (tmp_path / "1.fit").is_file()
    assert not (tmp_path.parent / "escape.fit").exists()


def test_timeout_fails_without_marking_import_complete(tmp_path, session, capsys):
    session.request.side_effect = requests.Timeout("request timed out")
    with pytest.raises(requests.Timeout):
        garmin.fetch_activities(tmp_path, 1)
    assert "importing" not in capsys.readouterr().out


@pytest.mark.parametrize("count", [0, -1, True, None])
def test_invalid_counts_make_no_requests(tmp_path, session, count):
    with pytest.raises(ValueError, match="count"):
        garmin.fetch_activities(tmp_path, count)
    session.request.assert_not_called()


def test_missing_key_makes_no_requests(tmp_path, session, monkeypatch):
    monkeypatch.delenv("GARMIN_CONNECT")
    with pytest.raises(ValueError, match="GARMIN_CONNECT"):
        garmin.fetch_activities(tmp_path, 1)
    session.request.assert_not_called()


@pytest.mark.skipif(
    not os.environ.get("GARMIN_SIMULATION_URL"),
    reason="requires local Postman simulation",
)
def test_real_downloader_against_postman_simulation(tmp_path, monkeypatch):
    monkeypatch.setattr(garmin, "BASE_URL", os.environ["GARMIN_SIMULATION_URL"])
    monkeypatch.setenv("GARMIN_CONNECT", "test-key")
    garmin.fetch_activities(tmp_path, 2)
    assert len(list(tmp_path.iterdir())) == 3
    assert json.loads((tmp_path / "activity_123.json").read_text())["activityId"] == 123
    assert (tmp_path / "123.fit").read_bytes()[8:12] == b".FIT"
    garmin.fetch_activities(tmp_path, 2)
    for key, status in [("revoked-key", 401), ("rate-limited-key", 429)]:
        monkeypatch.setenv("GARMIN_CONNECT", key)
        with pytest.raises(ValueError, match=f"HTTP {status}"):
            garmin.fetch_activities(tmp_path, 2)
        assert len(list(tmp_path.iterdir())) == 3


@pytest.mark.parametrize("key", ["key\nprivate", "kéy"])
def test_invalid_keys_are_rejected_without_echoing_value(
    tmp_path, session, monkeypatch, key
):
    monkeypatch.setenv("GARMIN_CONNECT", key)
    with pytest.raises(ValueError, match="without whitespace") as error:
        garmin.fetch_activities(tmp_path, 1)
    assert key not in str(error.value)
    session.request.assert_not_called()


@pytest.mark.parametrize("token", ["", "token\nprivate"])
def test_invalid_token_fails_before_activity_download(tmp_path, session, token):
    session.request.return_value = create_response(text=token)
    with pytest.raises(ValueError, match="invalid access token"):
        garmin.fetch_activities(tmp_path, 1)
    assert session.request.call_count == 1


@pytest.mark.parametrize("details", [None, [], {"activityId": 2}])
def test_invalid_details_are_not_saved(tmp_path, session, details):
    session.request.side_effect = [
        create_response(),
        create_response([{"activityId": 1}]),
        create_response(details),
    ]
    with pytest.raises(ValueError, match="invalid activity details"):
        garmin.fetch_activities(tmp_path, 1)
    assert not (tmp_path / "activity_details_1.json").exists()
