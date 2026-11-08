"""Check Garmin SDK field conversions used for multisport FIT files."""

from datetime import UTC, datetime, time
from types import SimpleNamespace

import pytest

from weather_score.fit_multisport import (
    _device_fields,
    _fields,
    _time,
    _zones,
    decode_multisport,
)


def test_sdk_units_are_mapped_to_existing_activity_units():
    result = _fields(
        {
            "distance": 1234,
            "position_lat": 2**30,
            "enhanced_speed": [2.5, None],
            "enhanced_altitude": 45.0,
            "total_elapsed_time": 61.25,
            "avg_stance_time": 200.0,
        }
    )
    assert result["distance"] == 1.234
    assert result["position_lat"] == 90
    assert result["speed"] == 9
    assert result["altitude"] == 45
    assert result["total_elapsed_time"] == time(0, 1, 1, 250000)
    assert result["avg_stance_time"] == time(0, 0, 0, 200000)


def test_sdk_device_and_zone_enums_are_mapped():
    device = _device_fields(
        {
            "manufacturer": "garmin",
            "garmin_product": 3992,
            "source_type": "local",
            "device_type": 4,
        }
    )
    assert device["manufacturer"] == "Garmin"
    assert device["device_type"].name == "barometer"
    zone = _zones(
        {
            "reference_mesg": "lap",
            "reference_index": 2,
            "time_in_hr_zone": [0, 1, 2, 3, 4, 5],
            "hr_calc_type": "percent_max_hr",
        }
    )
    assert zone.fields["hr_zones_method"] == "max_heart_rate"
    assert zone.fields["hr_zones_time"][1] == time(0, 0, 1)


def test_sdk_rejects_unrepresentable_duration_and_unknown_zone_method():
    with pytest.raises(ValueError, match="duration"):
        _time(86400)
    with pytest.raises(ValueError, match="zone method"):
        _zones(
            {
                "reference_mesg": "session",
                "time_in_hr_zone": [0] * 6,
                "hr_calc_type": "future_method",
            }
        )


def test_sdk_unsigned_timezone_and_decoder_errors(monkeypatch, tmp_path):
    monkeypatch.setattr("weather_score.fit_multisport.Stream.from_file", lambda _: None)
    data = {
        "session_mesgs": [{}, {}],
        "file_id_mesgs": [{}],
        "device_settings_mesgs": [{"time_offset": 2**32 - 18000}],
    }
    monkeypatch.setattr(
        "weather_score.fit_multisport.Decoder",
        lambda _: SimpleNamespace(read=lambda: (data, [])),
    )
    fit = decode_multisport(tmp_path / "activity.fit")
    assert fit.utc_datetime_to_local(
        datetime(2023, 9, 2, 13, 15, tzinfo=UTC)
    ) == datetime.fromisoformat("2023-09-02 08:15:00")
    data.pop("device_settings_mesgs")
    data["session_mesgs"][0]["start_time"] = datetime(2023, 9, 2, 13, 15, tzinfo=UTC)
    fit = decode_multisport(tmp_path / "activity.fit", "2023-09-02 08:15:00")
    assert fit.utc_datetime_to_local(
        datetime(2023, 9, 2, 13, 15, tzinfo=UTC)
    ) == datetime.fromisoformat("2023-09-02 08:15:00")
    with pytest.raises(ValueError, match="no usable local time offset"):
        decode_multisport(tmp_path / "activity.fit")
    monkeypatch.setattr(
        "weather_score.fit_multisport.Decoder",
        lambda _: SimpleNamespace(read=lambda: ({}, ["error"])),
    )
    with pytest.raises(ValueError, match="decoder rejected"):
        decode_multisport(tmp_path / "activity.fit")
