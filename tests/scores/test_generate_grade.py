from copy import deepcopy

import pytest

from weather_score.application.main import generate_grade


def conditions(**overrides):
    current = {
        "temp_c": 7,
        "humidity": 50,
        "precip_mm": 0,
        "gust_kph": 0,
    }
    current.update(overrides)
    return {"current": current}


@pytest.mark.asyncio
async def test_ideal_conditions_score_100():
    assert await generate_grade(conditions(), {"elevation": [0]}) == 100


@pytest.mark.asyncio
async def test_combines_all_penalties():
    weather = conditions(temp_c=20, humidity=75, precip_mm=10, gust_kph=36)

    assert await generate_grade(weather, {"elevation": [1000]}) == 75.33


@pytest.mark.asyncio
async def test_extreme_conditions_are_clamped_to_zero():
    weather = conditions(temp_c=60, humidity=100, precip_mm=100, gust_kph=300)

    assert await generate_grade(weather, {"elevation": [9000]}) == 0


@pytest.mark.asyncio
async def test_inputs_are_not_modified():
    weather = conditions()
    altitude = {"elevation": [100]}
    original_weather = deepcopy(weather)
    original_altitude = deepcopy(altitude)

    await generate_grade(weather, altitude)

    assert weather == original_weather
    assert altitude == original_altitude


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("weather", "altitude"),
    [
        ({}, {"elevation": [0]}),
        ({"current": None}, {"elevation": [0]}),
        (conditions(temp_c=None), {"elevation": [0]}),
        (conditions(humidity=None), {"elevation": [0]}),
        (conditions(precip_mm=None), {"elevation": [0]}),
        (conditions(gust_kph=None), {"elevation": [0]}),
        (conditions(), {}),
        (conditions(), {"elevation": []}),
        (conditions(), {"elevation": [None]}),
    ],
)
async def test_rejects_missing_weather_or_altitude_values(weather, altitude):
    with pytest.raises((TypeError, ValueError)):
        await generate_grade(weather, altitude)
