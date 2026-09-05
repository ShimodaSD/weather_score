import pytest

from weather_score.application.main import humidity_interaction_penalty


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "temperature, humidity, expected",
    [
        (10, 100, 0),
        (20, 100, 0),
        (30, 0, 0),
        (30, 50, 0),
        (21, 51, 0.01),
        (25, 75, 1.25),
        (30, 100, 5),
        (40, 100, 10),
    ],
)
async def test_humidity_interaction_penalty(temperature, humidity, expected):
    assert await humidity_interaction_penalty(temperature, humidity) == pytest.approx(
        expected
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("humidity", [-1, 101, None, "humid"])
async def test_humidity_penalty_rejects_invalid_humidity(humidity):
    with pytest.raises((TypeError, ValueError)):
        await humidity_interaction_penalty(25, humidity)


@pytest.mark.asyncio
async def test_humidity_penalty_rejects_invalid_temperature():
    with pytest.raises(TypeError):
        await humidity_interaction_penalty(None, 50)
