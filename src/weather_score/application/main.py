import asyncio
import math
from dataclasses import dataclass
from numbers import Real


def _number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a number.")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite.")
    return number


def _weather_values(weather: dict, altitude_data: dict) -> tuple[float, ...]:
    current = weather.get("current")
    if not isinstance(current, dict):
        raise TypeError("Weather data must contain current conditions.")

    elevation = altitude_data.get("elevation")
    if not isinstance(elevation, list) or not elevation:
        raise ValueError("Altitude data must contain an elevation.")

    return (
        _number("temperature", current.get("temp_c")),
        _number("humidity", current.get("humidity")),
        _number("precipitation", current.get("precip_mm")),
        _number("gust", current.get("gust_kph")),
        _number("altitude", elevation[0]),
    )


async def calculate_activity_score(weather, altitude_data) -> float:
    return (await calculate_activity_score_breakdown(weather, altitude_data)).score


@dataclass(frozen=True, slots=True)
class ActivityScoreBreakdown:
    score: float
    temperature_c: float
    humidity_percent: float
    precipitation_mm: float
    wind_gust_kph: float
    altitude_m: float
    temperature_penalty: float
    wind_penalty: float
    humidity_penalty: float
    altitude_penalty: float
    precipitation_penalty: float


async def calculate_activity_score_breakdown(weather, altitude_data) -> ActivityScoreBreakdown:
    temp, humidity, precipitation, gust, altitude = _weather_values(
        weather, altitude_data
    )

    (
        temp_loss,
        wind_loss,
        humidity_loss,
        altitude_loss,
        precipitation_loss,
    ) = await asyncio.gather(
        calculate_temperature_penalty(temp),
        calculate_wind_penalty(gust / 3.6),
        calculate_humidity_interaction_penalty(temp, humidity),
        calculate_altitude_penalty(altitude),
        calculate_rain_penalty(precipitation),
    )

    score = max(0.0, min(100.0, 100 - temp_loss - wind_loss - humidity_loss - altitude_loss - precipitation_loss))
    return ActivityScoreBreakdown(
        score=round(score, 2),
        temperature_c=temp,
        humidity_percent=humidity,
        precipitation_mm=precipitation,
        wind_gust_kph=gust,
        altitude_m=altitude,
        temperature_penalty=round(temp_loss, 2),
        wind_penalty=round(wind_loss, 2),
        humidity_penalty=round(humidity_loss, 2),
        altitude_penalty=round(altitude_loss, 2),
        precipitation_penalty=round(precipitation_loss, 2),
    )


async def calculate_temperature_penalty(temperature_c: float) -> float:
    temperature_c = _number("temperature", temperature_c)
    return max(0, 0.0125 * temperature_c**2 - 0.07893 * temperature_c - 0.15)


async def calculate_wind_penalty(gust_kph: float) -> float:
    gust_kph = _number("gust", gust_kph)
    if gust_kph < 0:
        raise ValueError("gust cannot be negative.")
    return 0.1 * gust_kph**2 + 0.66 * gust_kph


async def calculate_humidity_interaction_penalty(
    temperature_c: float,
    relative_humidity: float,
) -> float:
    temperature_c = _number("temperature", temperature_c)
    relative_humidity = _number("humidity", relative_humidity)
    if not 0 <= relative_humidity <= 100:
        raise ValueError("humidity must be between 0 and 100.")
    temp_factor = max(0.0, temperature_c - 20.0) / 10.0
    humidity_factor = max(0.0, relative_humidity - 50.0) / 50.0

    penalty = 5.0 * temp_factor * humidity_factor

    return penalty


async def calculate_altitude_penalty(altitude_m: float) -> float:
    altitude_m = _number("altitude", altitude_m)
    if altitude_m <= 500:
        return 0.0

    return 0.003 * (altitude_m - 500)


async def calculate_rain_penalty(precip_mm: float) -> float:
    precip_mm = _number("precipitation", precip_mm)
    if precip_mm < 0:
        raise ValueError("precipitation cannot be negative.")
    return min(0.33 * precip_mm, 5.0)
