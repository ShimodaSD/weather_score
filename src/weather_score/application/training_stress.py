"""Activity training load calculations."""

from collections.abc import Iterable
from math import isfinite


def _validate_number(value: object, name: str, *, allow_zero: bool = False) -> float:
    if value is None:
        raise ValueError(f"{name} is required.")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number.")
    try:
        number = float(value)
    except OverflowError as error:
        raise ValueError(f"{name} is too large.") from error
    if not isfinite(number) or number < 0 or (number == 0 and not allow_zero):
        raise ValueError(
            f"{name} must be finite and {'non-negative' if allow_zero else 'positive'}."
        )
    return number


def calculate_tss_total(
    activities: Iterable[dict[str, object]], threshold_heart_rate_bpm: int
) -> dict[str, object]:
    """Sum available heart-rate estimates and report activities excluded from the total."""
    threshold = _validate_number(threshold_heart_rate_bpm, "Threshold heart rate")
    if not 30 <= threshold <= 250:
        raise ValueError("Threshold heart rate must be between 30 and 250 bpm.")
    total = 0.0
    scored = 0
    excluded = 0
    for activity in activities:
        try:
            result = calculate_activity_tss(
                activity.get("activity_type"),
                threshold_heart_rate_bpm=threshold,
                average_heart_rate_bpm=activity.get("average_heart_rate_bpm"),
                elapsed_seconds=activity.get("elapsed_seconds"),
            )
        except (TypeError, ValueError):
            excluded += 1
            continue
        total += result["tss"]
        scored += 1
    if not isfinite(total):
        raise ValueError("Total TSS is too large.")
    return {
        "tss": round(total, 2) if scored or not excluded else None,
        "scored_activity_count": scored,
        "excluded_activity_count": excluded,
    }


def calculate_activity_tss(
    activity_type: str,
    *,
    moving_seconds: float | None = None,
    distance_km: float | None = None,
    threshold_pace_seconds_per_km: float | None = None,
    ftp_watts: float | None = None,
    normalized_power_watts: float | None = None,
    duration_seconds: float | None = None,
    threshold_heart_rate_bpm: float | None = None,
    average_heart_rate_bpm: float | None = None,
    elapsed_seconds: float | None = None,
) -> dict[str, object]:
    """Calculate training load from an explicit heart rate, pace or power threshold."""
    if activity_type not in {"running", "cycling"}:
        raise ValueError("TSS is currently supported for running and cycling only.")
    hourly_load = None
    if threshold_heart_rate_bpm is not None:
        if any(
            value is not None
            for value in (
                threshold_pace_seconds_per_km,
                ftp_watts,
                normalized_power_watts,
                duration_seconds,
            )
        ):
            raise ValueError("Heart rate cannot be combined with pace or power inputs.")
        threshold = _validate_number(threshold_heart_rate_bpm, "Threshold heart rate")
        intensity = _validate_number(
            average_heart_rate_bpm, "Recorded average heart rate"
        )
        if not 30 <= threshold <= 250 or not 30 <= intensity <= 250:
            raise ValueError("Heart rates must be between 30 and 250 bpm.")
        duration = _validate_number(elapsed_seconds, "Recorded elapsed time")
        factor = intensity / threshold
        boundaries = (
            (0.85, 0.90, 0.95, 1.0, 1.03)
            if activity_type == "running"
            else (0.81, 0.90, 0.94, 1.0, 1.03)
        )
        zone = sum(factor >= boundary for boundary in boundaries) + (factor > 1.06)
        hourly_load = (30, 55, 70, 80, 100, 120, 140)[zone]
        method = "heart_rate_estimate"
        unit = "bpm"
        warnings = [
            (
                "Heart-rate-zone estimate from average heart rate, not TrainingPeaks hrTSS. "
                "Intervals and heart-rate drift are not resolved."
            ),
            "Recorded elapsed time includes pauses and may overestimate load.",
        ]
    elif activity_type == "running":
        if any(
            value is not None
            for value in (ftp_watts, normalized_power_watts, duration_seconds)
        ):
            raise ValueError(
                "Running uses recorded moving time and threshold pace only."
            )
        duration = _validate_number(moving_seconds, "Recorded moving time")
        distance = _validate_number(distance_km, "Recorded distance")
        threshold = _validate_number(threshold_pace_seconds_per_km, "Threshold pace")
        intensity = distance * 1000 / duration
        factor = distance * threshold / duration
        method = "running_pace_estimate"
        warnings = [
            (
                "Average pace estimate: hills, intervals, wind and heat are not adjusted. "
                "This is not normalized graded pace or TrainingPeaks rTSS."
            )
        ]
        unit = "m/s"
        threshold = 1000 / threshold
    elif activity_type == "cycling":
        if threshold_pace_seconds_per_km is not None:
            raise ValueError(
                "Cycling uses FTP, normalized power and timer duration only."
            )
        duration = _validate_number(duration_seconds, "Cycling timer duration")
        threshold = _validate_number(ftp_watts, "Cycling FTP")
        intensity = _validate_number(
            normalized_power_watts, "Normalized power", allow_zero=True
        )
        factor = intensity / threshold
        method = "cycling_power"
        unit = "W"
        warnings = [
            (
                "Use normalized power and timer duration from the same recording, "
                "including zero-power coasting. Average power is not a substitute."
            )
        ]
    try:
        tss = (
            duration
            / 3600
            * (hourly_load if hourly_load is not None else factor**2 * 100)
        )
    except OverflowError as error:
        raise ValueError("Inputs are too extreme to calculate TSS.") from error
    if not all(isfinite(value) for value in (tss, factor, intensity, threshold)):
        raise ValueError("Inputs are too extreme to calculate TSS.")
    return {
        "tss": round(tss, 2),
        "method": method,
        "duration_seconds": duration,
        "intensity_factor": factor,
        "intensity": intensity,
        "threshold": threshold,
        "intensity_unit": unit,
        "warnings": warnings,
    }
