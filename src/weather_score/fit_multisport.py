"""Read multisport FIT files using Garmin's official decoder."""

from datetime import UTC, datetime, time, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fitfile import AntplusDeviceType, GarminProduct, LocalDeviceType, MainDeviceType
from garmin_fit_sdk import Decoder, Stream


def _time(value: float | None, *, milliseconds: bool = False) -> time | None:
    if value is None:
        return None
    seconds = value / 1000 if milliseconds else value
    if not 0 <= seconds < 86400:
        raise ValueError("FIT duration cannot be represented by the existing database")
    return (datetime.min.replace(tzinfo=UTC) + timedelta(seconds=seconds)).time()


def _scalar(value: Any) -> Any:
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _fields(values: dict[Any, Any]) -> dict[str, Any]:
    result = {key: value for key, value in values.items() if isinstance(key, str)}
    for key in ("total_elapsed_time", "total_timer_time", "cum_operating_time"):
        if key in result:
            result[key] = _time(result[key])
    if "avg_stance_time" in result:
        result["avg_stance_time"] = _time(result["avg_stance_time"], milliseconds=True)
    for key in ("distance", "total_distance"):
        if result.get(key) is not None:
            result[key] /= 1000
    for key in (
        "position_lat",
        "position_long",
        "start_position_lat",
        "start_position_long",
        "end_position_lat",
        "end_position_long",
    ):
        if result.get(key) is not None:
            result[key] *= 180 / 2**31
    for key in ("speed", "avg_speed", "max_speed"):
        value = _scalar(result.get(key))
        if value is None:
            value = _scalar(result.get("enhanced_" + key))
        if value is not None:
            result[key] = value * 3.6
    if result.get("altitude") is None and result.get("enhanced_altitude") is not None:
        result["altitude"] = result["enhanced_altitude"]
    return result


def _device_fields(values: dict[Any, Any]) -> dict[str, Any]:
    result = _fields(values)
    manufacturer = result.get("manufacturer")
    if isinstance(manufacturer, str) and manufacturer.casefold() == "garmin":
        result["manufacturer"] = "Garmin"
    product = result.get("garmin_product", result.get("product"))
    if isinstance(product, int) and result.get("manufacturer") == "Garmin":
        try:
            result["product"] = GarminProduct(product)
        except ValueError:
            result["product"] = str(product)
    device_type = result.get("device_type")
    source = result.get("source_type")
    if isinstance(device_type, int):
        enum = LocalDeviceType if source == "local" else AntplusDeviceType
        try:
            result["device_type"] = enum(device_type)
        except ValueError as error:
            raise ValueError("Unsupported FIT device type") from error
    elif device_type is None and source == "local":
        result["device_type"] = MainDeviceType.fitness_tracker
    return result


def _zones(values: dict[str, Any]) -> Any | None:
    kind = values.get("reference_mesg")
    if kind not in ("session", "lap"):
        return None
    durations = values.get("time_in_hr_zone")
    if not isinstance(durations, list) or len(durations) < 6:
        raise ValueError("Incomplete FIT heart-rate zones")
    method = values.get("hr_calc_type")
    methods = {
        "custom": "custom",
        "percent_max_hr": "max_heart_rate",
        "percent_hrr": "heart_rate_reserve",
        "percent_lthr": "lactate_threshhold",
    }
    if method is not None and method not in methods:
        raise ValueError("Unsupported FIT heart-rate zone method")
    return SimpleNamespace(
        fields={
            "hr_zones_timer_type": kind,
            "record_num": values.get("reference_index"),
            "hr_zones_time": [_time(value) for value in durations],
            "hr_zones": values.get("hr_zone_high_boundary"),
            "hr_zones_method": methods.get(method),
        }
    )


def decode_multisport(path: Path, local_start: str | None = None) -> Any:
    """Adapt Garmin SDK messages to the existing multisport importer."""
    messages, errors = Decoder(Stream.from_file(str(path))).read()
    if errors:
        raise ValueError("Garmin FIT decoder rejected the file")
    sessions = messages.get("session_mesgs", [])
    file_ids = messages.get("file_id_mesgs", [])
    if len(sessions) < 2 or len(file_ids) != 1:
        raise ValueError("FIT file is not a supported multisport activity")
    settings = messages.get("device_settings_mesgs", [])
    offsets = settings[0].get("time_offset") if settings else None
    if offsets == []:
        offsets = None
    if isinstance(offsets, list) and offsets:
        index = settings[0].get("active_time_zone") or 0
        if not isinstance(index, int) or not 0 <= index < len(offsets):
            raise ValueError("Invalid FIT active time zone")
        offset = offsets[index]
    elif offsets is not None:
        offset = offsets
    else:
        start = sessions[0].get("start_time")
        if not local_start or not isinstance(start, datetime):
            raise ValueError("FIT file has no usable local time offset")
        local = datetime.fromisoformat(local_start)
        if local.tzinfo is not None:
            raise ValueError("Activity local start time must not include a timezone")
        offset = int((local - start.replace(tzinfo=None)).total_seconds())
        if offset % 60:
            raise ValueError("FIT session start does not match the activity local time")
    if offset >= 2**31:
        offset -= 2**32
    local_tz = timezone(timedelta(seconds=offset))

    def local(value: datetime) -> datetime:
        return (
            value.astimezone(local_tz).replace(tzinfo=None) if value.tzinfo else value
        )

    def wrap(values: list[dict[Any, Any]], transform: Any = _fields) -> list[Any]:
        return [SimpleNamespace(fields=transform(value)) for value in values]

    zones = [_zones(value) for value in messages.get("time_in_zone_mesgs", [])]
    return SimpleNamespace(
        session=wrap(sessions),
        record=wrap(messages.get("record_mesgs", [])),
        lap=wrap(messages.get("lap_mesgs", [])),
        file_id=wrap(file_ids, _device_fields),
        device_info=wrap(messages.get("device_info_mesgs", []), _device_fields),
        hr_zones_timer=[zone for zone in zones if zone is not None],
        split=wrap(messages.get("split_mesgs", [])),
        utc_datetime_to_local=local,
    )
