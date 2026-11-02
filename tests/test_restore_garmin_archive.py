import io
import sys
import tarfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from restore_garmin_archive import restore_archive


def make_archive(path, members):
    with tarfile.open(path, "w:gz") as archive:
        for name, content in members:
            item = tarfile.TarInfo(name)
            item.size = len(content)
            archive.addfile(item, io.BytesIO(content))


def test_restores_files_and_preserves_existing_data(tmp_path):
    archive = tmp_path / "backup.tar.gz"
    destination = tmp_path / "activities"
    make_archive(archive, [("Activities/1.fit", b"fit"), ("Activities/.activity-list.json", b"cache")])
    assert restore_archive(archive, destination) == 1
    assert (destination / "1.fit").read_bytes() == b"fit"
    assert restore_archive(archive, destination) == 1
    (destination / "1.fit").write_bytes(b"different")
    with pytest.raises(FileExistsError):
        restore_archive(archive, destination)
    assert (destination / "1.fit").read_bytes() == b"different"


def test_rejects_archive_path_traversal(tmp_path):
    archive = tmp_path / "bad.tar.gz"
    make_archive(archive, [("Activities/../../escape", b"bad")])
    with pytest.raises(ValueError):
        restore_archive(archive, tmp_path / "activities")
    assert not (tmp_path / "escape").exists()
