from unittest.mock import MagicMock

import pytest

from scripts import archive_old_data as archive


@pytest.fixture
def configured_archive(monkeypatch):
    config = dict.fromkeys(
        ("DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"), "test"
    )
    monkeypatch.setattr(archive, "dotenv_values", lambda _: config)
    source, destination = MagicMock(), MagicMock()
    source.__enter__.return_value = source
    destination.__enter__.return_value = destination
    monkeypatch.setattr(
        archive.psycopg, "connect", MagicMock(side_effect=[source, destination])
    )
    monkeypatch.setattr(archive, "tables", lambda _: {("public", "activity_grades")})
    restore = MagicMock()
    delete = MagicMock()
    monkeypatch.setattr(archive, "restore_snapshot", restore)
    monkeypatch.setattr(archive, "delete_expired", delete)
    return source, restore, delete


def test_nothing_expired_does_not_create_or_delete(monkeypatch, configured_archive):
    _, restore, delete = configured_archive
    monkeypatch.setattr(archive, "has_expired", lambda *_: False)
    archive.main()
    restore.assert_not_called()
    delete.assert_not_called()


def test_mismatched_archive_never_deletes(monkeypatch, configured_archive):
    _, restore, delete = configured_archive
    monkeypatch.setattr(archive, "has_expired", lambda *_: True)
    monkeypatch.setattr(archive, "digest_remote", lambda *_: b"source")
    monkeypatch.setattr(archive, "digest_local", lambda *_: b"different")
    with pytest.raises(RuntimeError, match="verification failed"):
        archive.main()
    restore.assert_called_once()
    delete.assert_not_called()


def test_restore_failure_never_deletes(monkeypatch, configured_archive):
    _, restore, delete = configured_archive
    monkeypatch.setattr(archive, "has_expired", lambda *_: True)
    restore.side_effect = RuntimeError("restore failed")
    with pytest.raises(RuntimeError, match="restore failed"):
        archive.main()
    delete.assert_not_called()


def test_unexpected_tables_stop_retention():
    connection = MagicMock()
    expected = {
        (schema, table) for schema, names in archive.EXPECTED.items() for table in names
    }
    connection.execute.return_value.fetchall.return_value = list(
        expected | {("garmin", "new_data")}
    )
    with pytest.raises(RuntimeError, match="tables changed"):
        archive.tables(connection)


def test_restricted_role_cannot_archive_partial_rows(monkeypatch, configured_archive):
    source, restore, delete = configured_archive
    source.execute.return_value.fetchone.return_value = (False,)
    with pytest.raises(RuntimeError, match="cannot verify all protected rows"):
        archive.main()
    restore.assert_not_called()
    delete.assert_not_called()
