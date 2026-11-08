from unittest.mock import MagicMock

import idbutils.db
import pytest
from sqlalchemy import event

from scripts.garmindb_postgres import configure_schema_connections


def test_pooler_connections_set_schema_after_connect(monkeypatch):
    engine = MagicMock()
    create = MagicMock(return_value=engine)
    monkeypatch.setattr(idbutils.db, "create_engine", create)
    callbacks = []

    def listen(target, name):
        assert target is engine
        assert name == "connect"
        return lambda callback: callbacks.append(callback) or callback

    monkeypatch.setattr(event, "listens_for", listen)
    configure_schema_connections()
    configure_schema_connections()
    result = idbutils.db.create_engine("postgresql://example", connect_args={"options": "-csearch_path=garmin_activities"})
    assert result is engine
    assert idbutils.db.create_engine(
        "postgresql://example", connect_args={"options": "-csearch_path=garmin_activities"}
    ) is engine
    assert create.call_count == 1
    assert create.call_args.kwargs["connect_args"] == {}
    connection = MagicMock()
    callbacks[0](connection, None)
    connection.cursor.return_value.__enter__.return_value.execute.assert_called_once_with(
        'SET search_path TO "garmin_activities"'
    )
    connection.commit.assert_called_once()


def test_unknown_search_path_is_rejected(monkeypatch):
    create = MagicMock()
    monkeypatch.setattr(idbutils.db, "create_engine", create)
    configure_schema_connections()
    with pytest.raises(ValueError, match="Unexpected"):
        idbutils.db.create_engine("postgresql://example", connect_args={"options": "-csearch_path=public"})
    create.assert_not_called()
