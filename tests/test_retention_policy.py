import pytest

from scripts.retention_policy import DATED_TABLES, dated_delete


def test_complete_period_must_be_old_before_deleting():
    query = dated_delete("garmin_summary", "months_summary").as_string()
    assert "\"first_day\" + '1 month'::interval < %s" in query


def test_metadata_and_unknown_tables_cannot_be_selected():
    for schema, table in (("garmin", "devices"), ("public", "athlete_profile")):
        with pytest.raises(KeyError):
            dated_delete(schema, table)


def test_activity_children_are_not_date_deleted_independently():
    assert "garmin_activities" not in DATED_TABLES
