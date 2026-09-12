"""Predict running times with the Emig–Peltonen endurance model."""

from datetime import datetime, timedelta
from math import exp, isfinite, log

BENCHMARK_DISTANCES_KM = (5.0, 10.0, 21.0975, 42.195)
TARGET_DISTANCES_KM = (5.0, 10.0, 21.0, 42.0)
CROSSOVER_SECONDS = 360.0
GAMMA_BOUNDS = (0.039, 0.135)


def _predict_time(distance_km: float, vm: float, gamma: float) -> float | None:
    target_metres = distance_km * 1000

    def covered(seconds: float) -> float:
        return vm * seconds * (1 - gamma * log(seconds / CROSSOVER_SECONDS))

    low, high = CROSSOVER_SECONDS, 48 * 3600.0
    if covered(low) > target_metres or covered(high) < target_metres:
        return None
    for _ in range(60):
        middle = (low + high) / 2
        if covered(middle) < target_metres:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def _fit_model(benchmarks: list[dict[str, object]]) -> tuple[float, float] | None:
    if len(benchmarks) < 2:
        return None
    x = [log(effort["moving_seconds"] / CROSSOVER_SECONDS) for effort in benchmarks]
    y = [
        effort["distance_km"] * 1000 / effort["moving_seconds"] for effort in benchmarks
    ]
    mean_x, mean_y = sum(x) / len(x), sum(y) / len(y)
    variance = sum((value - mean_x) ** 2 for value in x)
    if variance <= 0:
        return None
    slope = (
        sum((value - mean_x) * (speed - mean_y) for value, speed in zip(x, y))
        / variance
    )
    vm = mean_y - slope * mean_x
    gamma = -slope / vm if vm > 0 else 0
    if not (2 < vm < 7 and GAMMA_BOUNDS[0] < gamma < GAMMA_BOUNDS[1]):
        return None
    predicted = [
        _predict_time(effort["distance_km"], vm, gamma) for effort in benchmarks
    ]
    if (
        any(time is None for time in predicted)
        or sum(
            abs(time - effort["moving_seconds"]) / effort["moving_seconds"]
            for time, effort in zip(predicted, benchmarks)
        )
        / len(benchmarks)
        > 0.05
    ):
        return None
    return vm, gamma


def calculate_running_predictions(runs: list[dict[str, object]]) -> dict[str, object]:
    """Fit the study model to recent race-distance efforts, or return bounded ranges."""
    valid = []
    for run in runs:
        distance, moving = run.get("distance_km"), run.get("moving_seconds")
        if (
            not isinstance(distance, (int, float))
            or isinstance(distance, bool)
            or not isfinite(distance)
            or distance < 3
            or not isinstance(moving, (int, float))
            or isinstance(moving, bool)
            or not isfinite(moving)
            or moving <= 0
            or not isinstance(run.get("activity_id"), str)
            or not isinstance(run.get("started_at"), datetime)
        ):
            continue
        valid.append(run)
    if not valid:
        return {
            "run_count": 0,
            "longest_run_km": None,
            "season_start_at": None,
            "season_end_at": None,
            "model_status": "no_benchmark",
            "vm_mps": None,
            "endurance_index": None,
            "basis": [],
            "predictions": [],
        }

    season_end = max(run["started_at"] for run in valid)
    season_start = season_end - timedelta(days=180)
    season = [run for run in valid if run["started_at"] >= season_start]
    benchmarks = []
    for target in BENCHMARK_DISTANCES_KM:
        candidates = [
            run
            for run in season
            if abs(run["distance_km"] / target - 1) <= 0.03
            and run["moving_seconds"] > CROSSOVER_SECONDS
        ]
        if candidates:
            source = min(candidates, key=lambda run: run["moving_seconds"])
            benchmarks.append(
                {
                    "distance_km": target,
                    "moving_seconds": source["moving_seconds"],
                    "source_activity_id": source["activity_id"],
                    "source_distance_km": source["distance_km"],
                    "source_started_at": source["started_at"],
                }
            )

    fit = _fit_model(benchmarks)
    anchor = (
        max(benchmarks, key=lambda effort: effort["distance_km"])
        if benchmarks
        else None
    )
    basis = benchmarks if fit else [anchor] if anchor else []
    predictions = []
    for target in TARGET_DISTANCES_KM if basis else ():
        if fit:
            times = [_predict_time(target, *fit)]
        elif target == anchor["distance_km"]:
            times = [anchor["moving_seconds"], anchor["moving_seconds"]]
        else:
            times = []
            for gamma in GAMMA_BOUNDS:
                speed = anchor["distance_km"] * 1000 / anchor["moving_seconds"]
                vm = speed / (
                    1 - gamma * log(anchor["moving_seconds"] / CROSSOVER_SECONDS)
                )
                times.append(_predict_time(target, vm, gamma))
        if any(time is None or not isfinite(time) for time in times):
            continue
        predictions.append(
            {
                "distance_km": target,
                "predicted_seconds": times[0] if fit else None,
                "low_seconds": min(times),
                "high_seconds": max(times),
            }
        )

    return {
        "run_count": len(season),
        "longest_run_km": max(run["distance_km"] for run in season),
        "season_start_at": season_start,
        "season_end_at": season_end,
        "model_status": "fitted" if fit else "range" if anchor else "no_benchmark",
        "vm_mps": fit[0] if fit else None,
        "endurance_index": exp(0.1 / fit[1]) if fit else None,
        "basis": basis,
        "predictions": predictions,
    }
