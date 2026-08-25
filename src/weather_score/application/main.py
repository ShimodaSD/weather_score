import asyncio


async def generate_grade(weather, altitude_data) -> float:
    humidity = weather.get("current").get("humidity")
    temp = weather.get("current").get("temp_c")
    precipitation = weather.get("current").get("precip_mm")
    gust = weather.get("current").get("gust_kph")

    (
        temp_loss,
        wind_loss,
        humidity_loss,
        altitude_loss,
        precipitation_loss,
    ) = await asyncio.gather(
        temperature_penalty(temp),
        wind_penalty(gust / 3.6),
        humidity_penalty(temp, humidity),
        altitude_penalty(altitude_data.get("elevation")[0]),
        rain_penalty(precipitation),
    )

    return round(
        100
        - (temp_loss + wind_loss + humidity_loss + altitude_loss + precipitation_loss),
        2,
    )


async def temperature_penalty(temperature_c: float) -> float:
    return max(0, 0.0125 * temperature_c**2 - 0.07893 * temperature_c - 0.15)


async def wind_penalty(gust_kph: float) -> float:
    return 0.1 * gust_kph**2 + 0.66 * gust_kph


async def humidity_penalty(temperature_c: float, humidity: float) -> float:
    temp = max(0, min(1, (temperature_c - 20) / 11))
    rh = max(0, min(1, (humidity - 40) / 31))

    return temp * rh**2


async def altitude_penalty(altitude_m: float) -> float:
    if altitude_m <= 500:
        return 0.0

    return 0.003 * (altitude_m - 500)


async def rain_penalty(precip_mm: float) -> float:
    return min(0.33 * precip_mm, 5.0)
