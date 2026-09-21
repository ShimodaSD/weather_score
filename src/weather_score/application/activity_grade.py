"""Route segmentation for weather-aware Garmin activity grades."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from math import atan, atan2, cos, degrees, isfinite, radians, sin
from numbers import Real


@dataclass(frozen=True, slots=True)
class ActivitySegment:
    """A route section ending at a recorded Garmin location."""

    index: int
    start_distance_m: float
    end_distance_m: float
    distance_m: float
    elapsed_seconds: float
    pace_minutes_per_km: float
    latitude: float
    longitude: float
    route_bearing_degrees: float
    recorded_at: datetime


def build_activity_segments(
    records: list[Mapping[str, object]], segment_metres: float = 200
) -> list[ActivitySegment]:
    """Split ordered Garmin samples into full distance-based route segments."""
    if not isfinite(segment_metres) or segment_metres <= 0:
        raise ValueError("segment metres must be finite and greater than zero")

    points = [_point(record) for record in records]
    points = [point for point in points if point is not None]
    if len(points) < 2:
        raise ValueError("activity needs at least two located records")

    points.sort(key=lambda point: (point[0], point[1]))
    origin = points[0]
    anchor = origin
    target_km = origin[0] + segment_metres / 1000
    segments: list[ActivitySegment] = []

    for point in points[1:]:
        if point[0] < target_km:
            continue
        distance_km = point[0] - anchor[0]
        elapsed_seconds = (point[1] - anchor[1]).total_seconds()
        if distance_km <= 0 or elapsed_seconds <= 0:
            raise ValueError("activity records must increase in distance and time")
        segments.append(
            ActivitySegment(
                index=len(segments) + 1,
                start_distance_m=round((anchor[0] - origin[0]) * 1000, 1),
                end_distance_m=round((point[0] - origin[0]) * 1000, 1),
                distance_m=round(distance_km * 1000, 1),
                elapsed_seconds=round(elapsed_seconds, 1),
                pace_minutes_per_km=elapsed_seconds / 60 / distance_km,
                latitude=point[2],
                longitude=point[3],
                route_bearing_degrees=calculate_route_bearing(
                    anchor[2], anchor[3], point[2], point[3]
                ),
                recorded_at=point[1],
            )
        )
        anchor = point
        target_km = origin[0] + (len(segments) + 1) * segment_metres / 1000

    if not segments:
        raise ValueError("activity has no complete 200 metre segment")
    return segments


def calculate_route_bearing(
    start_latitude: float,
    start_longitude: float,
    end_latitude: float,
    end_longitude: float,
) -> float:
    """Calculate the initial compass bearing between two route positions."""
    start_latitude_radians = radians(start_latitude)
    end_latitude_radians = radians(end_latitude)
    longitude_delta = radians(end_longitude - start_longitude)
    x = sin(longitude_delta) * cos(end_latitude_radians)
    y = cos(start_latitude_radians) * sin(end_latitude_radians) - sin(
        start_latitude_radians
    ) * cos(end_latitude_radians) * cos(longitude_delta)
    return round((degrees(atan2(x, y)) + 360) % 360, 2)


def calculate_headwind_component(
    wind_speed_kph: float, wind_direction_degrees: float, route_bearing_degrees: float
) -> float:
    """Project wind from its source direction onto the route heading."""
    values = (wind_speed_kph, wind_direction_degrees, route_bearing_degrees)
    if not all(isfinite(value) for value in values):
        raise ValueError("wind speed, wind direction, and route bearing must be finite")
    if wind_speed_kph < 0:
        raise ValueError("wind speed cannot be negative")
    if not 0 <= wind_direction_degrees <= 360 or not 0 <= route_bearing_degrees < 360:
        raise ValueError("wind direction or route bearing is out of range")
    return round(
        wind_speed_kph * cos(radians(wind_direction_degrees - route_bearing_degrees)),
        2,
    )


def calculate_outdoor_wbgt(
    temperature_c: float,
    humidity_percent: float,
    wind_kph: float,
    uv_index: float,
    cloud_percent: float,
) -> float:
    """Estimate outdoor WBGT from normalized hourly weather conditions."""
    values = (temperature_c, humidity_percent, wind_kph, uv_index, cloud_percent)
    if not all(isfinite(value) for value in values):
        raise ValueError("WBGT inputs must be finite")
    if not -50 <= temperature_c <= 60:
        raise ValueError("temperature is out of range")
    if not 0 <= humidity_percent <= 100 or not 0 <= cloud_percent <= 100:
        raise ValueError("humidity or cloud cover is out of range")
    if wind_kph < 0 or uv_index < 0:
        raise ValueError("wind speed or UV index cannot be negative")

    wet_bulb_c = (
        temperature_c * atan(0.151977 * (humidity_percent + 8.313659) ** 0.5)
        + atan(temperature_c + humidity_percent)
        - atan(humidity_percent - 1.676331)
        + 0.00391838 * humidity_percent**1.5 * atan(0.023101 * humidity_percent)
        - 4.686035
    )
    solar_w_m2 = uv_index * (1 - cloud_percent / 100) * 40
    globe_c = temperature_c
    if cloud_percent < 80:
        globe_c += min(solar_w_m2 * 0.012 / max(wind_kph / 3.6, 0.5), 12)
    return round(0.7 * wet_bulb_c + 0.2 * globe_c + 0.1 * temperature_c, 2)


def _point(
    record: Mapping[str, object],
) -> tuple[float, datetime, float, float] | None:
    values = [
        record.get(name) for name in ("distance", "position_lat", "position_long")
    ]
    timestamp = record.get("timestamp")
    if timestamp is None or any(value is None for value in values):
        return None
    if not isinstance(timestamp, datetime):
        raise TypeError("record timestamp must be a datetime")
    if any(isinstance(value, bool) or not isinstance(value, Real) for value in values):
        raise TypeError("record distance and coordinates must be numbers")
    distance, latitude, longitude = (float(value) for value in values)
    if not all(isfinite(value) for value in (distance, latitude, longitude)):
        raise ValueError("record distance and coordinates must be finite")
    if distance < 0 or not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("record distance or coordinates are out of range")
    return distance, timestamp, latitude, longitude
