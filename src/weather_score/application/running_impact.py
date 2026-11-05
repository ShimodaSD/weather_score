"""Calculate study-based running training impulse."""

from datetime import datetime
from math import exp, isfinite

from weather_score.application.running_predictions import calculate_running_predictions


def calculate_running_impact(
    runs: list[dict[str, object]], coefficients: str
) -> dict[str, object]:
    """Estimate per-run training load using a fitted crossover speed."""
    model = calculate_running_predictions(runs)
    vm = model["vm_mps"]
    start, end = model["season_start_at"], model["season_end_at"]
    k1, k2 = (0.64, 1.92) if coefficients == "male" else (0.86, 1.67)
    activities = []
    if vm is not None:
        for run in runs:
            distance, seconds, started = (
                run.get("distance_km"),
                run.get("moving_seconds"),
                run.get("started_at"),
            )
            if not (
                isinstance(distance, (int, float))
                and not isinstance(distance, bool)
                and isfinite(distance)
                and distance >= 3
                and isinstance(seconds, (int, float))
                and not isinstance(seconds, bool)
                and isfinite(seconds)
                and seconds > 0
                and isinstance(started, datetime)
                and start <= started <= end
                and isinstance(run.get("activity_id"), str)
            ):
                continue
            ratio = distance * 1000 / seconds / vm
            if ratio > 3:
                continue
            activities.append(
                {
                    **run,
                    "relative_speed": ratio,
                    "trimp": seconds / 60 * k1 * ratio * exp(k2 * ratio),
                }
            )
    activities.sort(key=lambda item: item["started_at"], reverse=True)
    return {"model": model, "coefficients": coefficients, "activities": activities}
