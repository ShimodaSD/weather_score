import pytest

from weather_score.application.main import temperature_penalty


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "temperature, expected",
    [
        (-40, 23.0072),
        (-10, 1.8893),
        (0, 0),
        (7, 0),
        (8, 0.01856),
        (20, 3.2714),
        (30, 8.7321),
        (50, 27.1535),
    ],
)
async def test_temperature_penalty(temperature, expected):
    assert await temperature_penalty(temperature) == pytest.approx(expected, abs=0.001)


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [None, "hot", float("inf"), float("nan")])
async def test_temperature_penalty_rejects_invalid_values(value):
    with pytest.raises((TypeError, ValueError)):
        await temperature_penalty(value)
