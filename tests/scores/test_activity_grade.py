from datetime import UTC, datetime, timedelta

import pytest
from weather_score.application.activity_grade import (
    build_activity_segments,
    calculate_headwind_component,
    calculate_outdoor_wbgt,
)


def record(distance, seconds, latitude=-27.47, longitude=153.03):
    return {
        "distance": distance,
        "timestamp": datetime(2026, 9, 17, tzinfo=UTC) + timedelta(seconds=seconds),
        "position_lat": latitude,
        "position_long": longitude,
    }


def test_builds_one_segment_for_each_complete_200_metres():
    segments = build_activity_segments(
        [record(0, 0), record(0.1, 30), record(0.2, 60), record(0.4, 130)]
    )

    assert len(segments) == 2
    assert segments[0].distance_m == 200
    assert segments[0].pace_minutes_per_km == 5
    assert segments[1].start_distance_m == 200
    assert segments[1].end_distance_m == 400
    assert segments[1].pace_minutes_per_km == pytest.approx(70 / 60 / 0.2)


def test_ignores_missing_gps_samples_without_converting_them_to_zero():
    missing = record(0.1, 30)
    missing["position_lat"] = None

    segments = build_activity_segments([record(0, 0), missing, record(0.2, 60)])

    assert len(segments) == 1
    assert segments[0].latitude == -27.47


@pytest.mark.parametrize(
    ("records", "message"),
    [
        ([record(0, 0)], "at least two"),
        ([record(0, 0), record(0.2, 0)], "increase in distance and time"),
        ([record(0, 0), record(0.1, 30)], "no complete 200"),
        ([record(0, 0), record(0.2, 60, latitude=91)], "out of range"),
    ],
)
def test_rejects_missing_invalid_and_short_routes(records, message):
    with pytest.raises(ValueError, match=message):
        build_activity_segments(records)


def test_rejects_invalid_segment_size():
    with pytest.raises(ValueError, match="greater than zero"):
        build_activity_segments([record(0, 0), record(0.2, 60)], 0)


@pytest.mark.parametrize(
    ("wind_direction", "route_bearing", "expected"),
    [(0, 0, 20), (180, 0, -20), (90, 0, 0)],
)
def test_projects_wind_onto_route_direction(wind_direction, route_bearing, expected):
    assert calculate_headwind_component(20, wind_direction, route_bearing) == expected


def test_segment_records_route_bearing():
    segment = build_activity_segments(
        [record(0, 0, longitude=153), record(0.2, 60, longitude=153.01)]
    )[0]

    assert segment.route_bearing_degrees == pytest.approx(90, abs=0.01)


@pytest.mark.parametrize(
    "values",
    [(-1, 0, 0), (10, -1, 0), (10, 0, 360), (10, float("nan"), 0)],
)
def test_rejects_invalid_wind_projection(values):
    with pytest.raises(ValueError):
        calculate_headwind_component(*values)


def test_estimates_outdoor_wbgt_from_hourly_conditions():
    shaded = calculate_outdoor_wbgt(30, 70, 10, 0, 100)
    sunny = calculate_outdoor_wbgt(30, 70, 10, 8, 0)

    assert 20 < shaded < 30
    assert sunny > shaded


@pytest.mark.parametrize(
    "values",
    [
        (61, 50, 10, 1, 20),
        (20, 101, 10, 1, 20),
        (20, 50, -1, 1, 20),
        (20, 50, 10, -1, 20),
        (20, 50, 10, 1, 101),
        (float("nan"), 50, 10, 1, 20),
    ],
)
def test_rejects_invalid_wbgt_inputs(values):
    with pytest.raises(ValueError):
        calculate_outdoor_wbgt(*values)
