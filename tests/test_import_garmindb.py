from unittest.mock import MagicMock

import pytest
from scripts.import_garmindb import import_activity_json


@pytest.mark.parametrize("activity_id", [21808646880, "21808646880"])
def test_import_normalizes_ids_and_keeps_downloaded_data_unchanged(activity_id):
    processor = MagicMock()
    processor._activities_process_json.return_value = 1
    data = {"activityId": activity_id, "activityName": "Run"}

    assert import_activity_json(processor, data) == 1

    processor._activities_process_json.assert_called_once_with(
        {"activityId": "21808646880", "activityName": "Run"}
    )
    assert data["activityId"] == activity_id
    assert processor.garmin_act_db_session is (
        processor.garmin_act_db.managed_session.return_value.__enter__.return_value
    )


def test_import_preserves_upstream_errors():
    processor = MagicMock()
    processor._activities_process_json.side_effect = ValueError("invalid activity")
    with pytest.raises(ValueError, match="invalid activity"):
        import_activity_json(processor, {"activityId": 21808646880})
    processor.garmin_act_db.managed_session.return_value.__exit__.assert_called_once()
