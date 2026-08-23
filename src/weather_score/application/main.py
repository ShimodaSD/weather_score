async def generate_grade(weather, altitude_data) -> float:
    humidity = weather.get("current").get("humidity")
    temp = weather.get("current").get("temp_c")

    precipitation = weather.get("current").get("precip_mm")
    gust = weather.get("current").get("gust_kph")

    temp_loss = max(0, 0.0125 * temp**2 - 0.07893 * temp - 0.15)
    wind_loss = 0.1 * gust**2 + 0.66 * gust  # m/s
    humidity_loss = humidity_stress(temp, humidity)
    altitude_loss = altitude_penalty(altitude_data.get("altitude"))

    return 100 - (temp_loss + wind_loss + humidity_loss + altitude_loss)


def humidity_stress(temperature_c: float, humidity: float) -> float:
    temp = max(0, min(1, (temperature_c - 20) / 11))
    rh = max(0, min(1, (humidity - 40) / 31))

    return temp * rh**2


def altitude_penalty(altitude_m: float) -> float:
    if altitude_m <= 500:
        return 0.0

    return 0.003 * (altitude_m - 500)
