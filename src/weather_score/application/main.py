import asyncio
import math
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


async def generate_grade(weather, altitude_data) -> float:
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
        temperature_penalty(temp),
        wind_penalty(gust / 3.6),
        humidity_interaction_penalty(temp, humidity),
        altitude_penalty(altitude),
        rain_penalty(precipitation),
    )

    score = 100 - (
        temp_loss + wind_loss + humidity_loss + altitude_loss + precipitation_loss
    )
    return round(max(0.0, min(100.0, score)), 2)


async def generate_grade_by_type(weather, altitude_data, training_type: str) -> float:
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
        temperature_penalty(temp),
        wind_penalty(gust / 3.6),
        humidity_interaction_penalty(temp, humidity),
        altitude_penalty(altitude),
        rain_penalty(precipitation),
    )

    total_loss = (
        temp_loss + wind_loss + humidity_loss + altitude_loss + precipitation_loss
    )

    return round(max(0.0, min(100.0, 100 - total_loss)), 2)


async def temperature_penalty(temperature_c: float) -> float:
    temperature_c = _number("temperature", temperature_c)
    return max(0, 0.0125 * temperature_c**2 - 0.07893 * temperature_c - 0.15)


async def wind_penalty(gust_kph: float) -> float:
    gust_kph = _number("gust", gust_kph)
    if gust_kph < 0:
        raise ValueError("gust cannot be negative.")
    return 0.1 * gust_kph**2 + 0.66 * gust_kph


async def humidity_interaction_penalty(
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


async def altitude_penalty(altitude_m: float) -> float:
    altitude_m = _number("altitude", altitude_m)
    if altitude_m <= 500:
        return 0.0

    return 0.003 * (altitude_m - 500)


async def rain_penalty(precip_mm: float) -> float:
    precip_mm = _number("precipitation", precip_mm)
    if precip_mm < 0:
        raise ValueError("precipitation cannot be negative.")
    return min(0.33 * precip_mm, 5.0)
