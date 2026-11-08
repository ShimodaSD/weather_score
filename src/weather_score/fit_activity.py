"""Decode FIT activity samples without the GarminDB importer."""

from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

from fitfile import File

RECORD_FIELDS = {
    "position_lat": "position_lat",
    "position_long": "position_long",
    "distance": "distance",
    "cadence": "cadence",
    "altitude": "altitude",
    "hr": "heart_rate",
    "rr": "respiration_rate",
    "speed": "speed",
    "temperature": "temperature",
}

LAP_FIELDS = {
    "elapsed_time": "total_elapsed_time",
    "moving_time": "total_timer_time",
    "distance": "total_distance",
    "cycles": "total_cycles",
    "avg_hr": "avg_heart_rate",
    "max_hr": "max_heart_rate",
    "avg_rr": "avg_respiration_rate",
    "max_rr": "max_respiration_rate",
    "calories": "total_calories",
    "avg_cadence": "avg_cadence",
    "max_cadence": "max_cadence",
    "avg_speed": "avg_speed",
    "max_speed": "max_speed",
    "ascent": "total_ascent",
    "descent": "total_descent",
    "max_temperature": "max_temperature",
    "min_temperature": "min_temperature",
    "avg_temperature": "avg_temperature",
    "start_lat": "start_position_lat",
    "start_long": "start_position_long",
    "stop_lat": "end_position_lat",
    "stop_long": "end_position_long",
}


class UnsupportedMultisportError(ValueError):
    """A multisport FIT file cannot be safely partitioned."""


def decode_fit_sessions(fit: File) -> list[dict[str, list[dict[str, object]]]]:
    """Partition multisport records and laps into their FIT sessions without loss."""
    if len(fit.session) <= 1:
        return [decode_fit(fit)]
    windows = []
    lap_counts = []
    for session in fit.session:
        start = session.fields.get("start_time")
        elapsed = session.fields.get("total_elapsed_time")
        count = session.fields.get("num_laps")
        if start is None or elapsed is None or not isinstance(count, int) or count < 0:
            raise UnsupportedMultisportError(
                "Multisport session lacks timing or lap counts"
            )
        duration = timedelta(
            hours=elapsed.hour,
            minutes=elapsed.minute,
            seconds=elapsed.second,
            microseconds=elapsed.microsecond,
        )
        if duration <= timedelta(0):
            raise UnsupportedMultisportError("Multisport session has invalid duration")
        end = start + duration
        if windows and start < windows[-1][1] - timedelta(seconds=1):
            raise UnsupportedMultisportError("Multisport sessions overlap")
        windows.append((start, end))
        lap_counts.append(count)
    if sum(lap_counts) != len(fit.lap):
        raise UnsupportedMultisportError(
            "Multisport lap count does not match the FIT file"
        )

    grouped = [[] for _ in windows]
    for message in fit.record:
        timestamp = message.fields.get("timestamp")
        if timestamp is None:
            raise UnsupportedMultisportError("Multisport record has no timestamp")
        matches = [
            i for i, (start, end) in enumerate(windows) if start <= timestamp <= end
        ]
        if not matches:
            distances = [
                min(abs(timestamp - start), abs(timestamp - end))
                for start, end in windows
            ]
            nearest = min(range(len(distances)), key=distances.__getitem__)
            if distances[nearest] > timedelta(seconds=1):
                raise UnsupportedMultisportError(
                    "Multisport record falls outside session boundaries"
                )
            matches = [nearest]
        grouped[matches[-1]].append(message)

    output = []
    first_lap = 0
    for index, count in enumerate(lap_counts):
        laps = []
        for message in fit.lap[first_lap : first_lap + count]:
            fields = dict(message.fields)
            start = fields.get("start_time")
            elapsed = fields.get("total_elapsed_time")
            if start is None or elapsed is None:
                raise UnsupportedMultisportError("Multisport lap lacks timing")
            fields["timestamp"] = start + timedelta(
                hours=elapsed.hour,
                minutes=elapsed.minute,
                seconds=elapsed.second,
                microseconds=elapsed.microsecond,
            )
            laps.append(SimpleNamespace(fields=fields))
        first_lap += count
        session_fit = SimpleNamespace(
            session=[fit.session[index]],
            record=grouped[index],
            lap=laps,
            utc_datetime_to_local=fit.utc_datetime_to_local,
        )
        output.append(decode_fit(session_fit))
    return output


def decode_activity(path: Path) -> dict[str, list[dict[str, object]]]:
    """Decode one single-sport FIT file into existing record and lap fields."""
    return decode_fit(File(str(path)))


def decode_fit(fit: File) -> dict[str, list[dict[str, object]]]:
    """Convert an already parsed FIT file into activity records and laps."""
    if len(fit.session) > 1:
        raise UnsupportedMultisportError("Multisport FIT requires session decoding")

    records = []
    for index, message in enumerate(fit.record):
        fields = message.fields
        timestamp = fields.get("timestamp")
        records.append(
            {
                "record": index,
                "timestamp": fit.utc_datetime_to_local(timestamp)
                if timestamp
                else None,
                **{
                    column: fields.get(field) for column, field in RECORD_FIELDS.items()
                },
            }
        )

    laps = []
    for index, message in enumerate(fit.lap):
        fields = message.fields
        start = fields.get("start_time")
        stop = fields.get("timestamp")
        laps.append(
            {
                "lap": index,
                "start_time": fit.utc_datetime_to_local(start) if start else None,
                "stop_time": fit.utc_datetime_to_local(stop) if stop else None,
                **{
                    column: (None if fields.get(field) == 0 else fields.get(field))
                    for column, field in LAP_FIELDS.items()
                },
            }
        )
    return {"records": records, "laps": laps}
