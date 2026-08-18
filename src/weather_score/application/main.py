async def generate_grade(weather):
    wind = weather.get("current").get("wind_kph")
    humidity = weather.get("current").get("humidity")
    temp = weather.get("current").get("temp_c")
    pressure = weather.get("current").get("pressure_mb")
    precipitation = weather.get("current").get("precip_mm")
    wind_direction = weather.get("current").get("wind_dir")
