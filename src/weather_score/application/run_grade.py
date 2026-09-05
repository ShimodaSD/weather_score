"""Research-backed grading for outdoor running conditions.

The score estimates wind and thermal suitability. Pace is used to calculate
air speed relative to the runner, not to judge the runner's ability.
"""

from dataclasses import dataclass
from math import isfinite

_REFERENCE_AIR_SPEED_MPS = 21.5 / 3.6
_HEADWIND_PERCENT_PER_MPS_SQUARED = 2.2 / _REFERENCE_AIR_SPEED_MPS**2
_TAILWIND_PERCENT_PER_MPS_SQUARED = 3.1 / _REFERENCE_AIR_SPEED_MPS**2

_OPTIMAL_WBGT_C = 7.5
_HOT_LOSS_PERCENT_PER_C = 0.2
_COLD_LOSS_PERCENT_PER_C = 0.1


@dataclass(frozen=True, slots=True)
class RunGrade:
    """The calculated grade and its independently calculated factors."""

    score: float
    running_speed_kph: float
    relative_air_speed_kph: float
    wind_metabolic_change_percent: float
    thermal_performance_loss_percent: float


def calculate_run_grade(
    *,
    average_pace_minutes_per_km: float,
    headwind_kph: float,
    wet_bulb_globe_temperature_c: float,
) -> RunGrade:
    """Calculate a bounded outdoor-run suitability grade."""

    if not isfinite(average_pace_minutes_per_km):
        raise ValueError("average pace must be finite")
    if average_pace_minutes_per_km <= 0:
        raise ValueError("average pace must be greater than zero")
    if not isfinite(headwind_kph):
        raise ValueError("headwind must be finite")
    if not isfinite(wet_bulb_globe_temperature_c):
        raise ValueError("WBGT must be finite")
    if wet_bulb_globe_temperature_c < -50 or wet_bulb_globe_temperature_c > 60:
        raise ValueError("WBGT must be between -50 and 60 degrees Celsius")

    running_speed_mps = 1000 / (average_pace_minutes_per_km * 60)
    relative_air_speed_mps = max(0.0, running_speed_mps + headwind_kph / 3.6)

    if headwind_kph >= 0:
        wind_change = _HEADWIND_PERCENT_PER_MPS_SQUARED * (
            relative_air_speed_mps**2 - running_speed_mps**2
        )
    else:
        wind_change = -_TAILWIND_PERCENT_PER_MPS_SQUARED * (
            running_speed_mps**2 - relative_air_speed_mps**2
        )

    if wet_bulb_globe_temperature_c >= _OPTIMAL_WBGT_C:
        thermal_loss = (
            wet_bulb_globe_temperature_c - _OPTIMAL_WBGT_C
        ) * _HOT_LOSS_PERCENT_PER_C
    else:
        thermal_loss = (
            _OPTIMAL_WBGT_C - wet_bulb_globe_temperature_c
        ) * _COLD_LOSS_PERCENT_PER_C

    score = max(0.0, min(100.0, 100.0 - thermal_loss - max(0.0, wind_change)))

    return RunGrade(
        score=round(score, 2),
        running_speed_kph=round(running_speed_mps * 3.6, 2),
        relative_air_speed_kph=round(relative_air_speed_mps * 3.6, 2),
        wind_metabolic_change_percent=round(wind_change, 2),
        thermal_performance_loss_percent=round(thermal_loss, 2),
    )
