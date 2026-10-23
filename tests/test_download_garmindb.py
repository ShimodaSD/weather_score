import json
from pathlib import Path

import pytest
from scripts.download_garmindb import install_download_progress


def create_downloader(tmp_path, fail_binary=False, fail_details=False):
    class Downloader:
        def get_activities(self, directory, count, overwrite=False):
            self.temp_dir = str(tmp_path / "temp")
            Path(self.temp_dir).mkdir(exist_ok=True)
            for activity in self._Download__get_activity_summaries(0, count):
                activity_id = activity["activityId"]
                summary = Path(directory) / f"activity_{activity_id}"
                if not Path(f"{summary}.json").exists() or overwrite:
                    if not fail_details:
                        self.save_json_to_file(f"{directory}/activity_details_{activity_id}", {}, overwrite)
                    self.save_json_to_file(str(summary), activity)
                    if not Path(f"{directory}/{activity_id}.fit").exists() or overwrite:
                        self.save_binary_file(f"{self.temp_dir}/activity_{activity_id}.zip", "unused")

        def _Download__get_activity_summaries(self, start, count):
            return [{"activityId": 1}, {"activityId": 2}]

        @classmethod
        def save_json_to_file(cls, filename, data, overwrite=False):
            path = Path(f"{filename}.json")
            if overwrite or not path.exists():
                path.write_text(json.dumps(data))

        def save_binary_file(self, filename, url, overwrite=False):
            if fail_binary:
                raise OSError("download failed")
            Path(filename).write_bytes(b"archive")

    install_download_progress(Downloader)
    return Downloader()


def get_events(capsys):
    return [json.loads(line.split(": ", 1)[1]) for line in capsys.readouterr().out.splitlines()]


def test_counts_only_missing_files_and_reports_import_phase(tmp_path, capsys):
    (tmp_path / "activity_1.json").write_text("{}")
    (tmp_path / "activity_details_2.json").write_text("{}")
    downloader = create_downloader(tmp_path)
    downloader.get_activities(str(tmp_path), 2)
    events = get_events(capsys)
    assert events[0] == {"phase": "downloading", "downloaded_files": 0, "total_files": 2}
    assert events[-1] == {"phase": "importing", "downloaded_files": 2, "total_files": 2}


@pytest.mark.parametrize("overwrite, total", [(False, 0), (True, 4)])
def test_handles_existing_files_and_overwrite(tmp_path, capsys, overwrite, total):
    for activity_id in (1, 2):
        for filename in (f"activity_{activity_id}.json", f"activity_details_{activity_id}.json", f"{activity_id}.fit"):
            (tmp_path / filename).write_text("{}")
    create_downloader(tmp_path).get_activities(str(tmp_path), 2, overwrite=overwrite)
    assert get_events(capsys)[-1] == {"phase": "importing", "downloaded_files": total, "total_files": total}


@pytest.mark.parametrize("fail_binary, fail_details", [(True, False), (False, True)])
def test_never_counts_failed_downloads_as_complete(tmp_path, capsys, fail_binary, fail_details):
    downloader = create_downloader(tmp_path, fail_binary, fail_details)
    with pytest.raises((OSError, RuntimeError)):
        downloader.get_activities(str(tmp_path), 2)
    events = get_events(capsys)
    assert events[-1]["phase"] == "downloading"
    assert events[-1]["downloaded_files"] < events[-1]["total_files"]
