import tarfile

import pytest

from scripts.backup_garmin_archive import backup_activities


def test_backup_and_restore_round_trip(tmp_path):
    source = tmp_path / "Activities"
    source.mkdir()
    (source / "1.fit").write_bytes(b"fit data")
    (source / "activity_1.json").write_text('{}')
    (source / ".activity-list.json").write_text('[]')
    destination = tmp_path / "backups" / "activities.tar.gz"

    assert backup_activities(source, destination) == 2
    with tarfile.open(destination, "r:gz") as archive:
        assert sorted(archive.getnames()) == ["Activities/1.fit", "Activities/activity_1.json"]
        assert archive.extractfile("Activities/1.fit").read() == b"fit data"
    original = destination.read_bytes()
    with pytest.raises(FileExistsError):
        backup_activities(source, destination)
    assert destination.read_bytes() == original
    assert not list(destination.parent.glob('.garmin-backup-*'))
    assert destination.stat().st_mode & 0o077 == 0


def test_empty_source_is_rejected(tmp_path):
    source = tmp_path / "Activities"
    source.mkdir()
    with pytest.raises(ValueError, match="no files"):
        backup_activities(source, tmp_path / "backup.tar.gz")
