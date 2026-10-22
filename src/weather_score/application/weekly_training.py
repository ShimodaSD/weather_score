"""Calendar-week distances and training load for the activity dashboard."""

from datetime import date, timedelta
from math import isfinite

from weather_score.application.training_stress import calculate_tss_total


def calculate_weekly_training(
    activities: list[dict[str, object]], start: date, threshold: int
) -> list[dict[str, object]]:
    """Include empty weeks and preserve unavailable distances and TSS as null."""
    groups = [[] for _ in range(12)]
    for activity in activities:
        index = (activity["started_at"].date() - start).days // 7
        if 0 <= index < 12:
            groups[index].append(activity)
    weeks = []
    for index, group in enumerate(groups):
        week_start = start + timedelta(weeks=index)
        week = {
            "week_start": week_start,
            "week_end": week_start + timedelta(days=6),
            "threshold_heart_rate_bpm": threshold,
            **calculate_tss_total(group, threshold),
        }
        for sport in ("running", "cycling"):
            distances = [
                a.get("distance_km") for a in group if a["activity_type"] == sport
            ]
            valid = all(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and isfinite(value)
                and value >= 0
                for value in distances
            )
            week[f"{sport}_km"] = round(sum(distances), 2) if valid else None
        weeks.append(week)
    return weeks
