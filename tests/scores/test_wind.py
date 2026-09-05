import pytest

from weather_score.application.main import wind_penalty


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "gust, expected",
    [(0, 0), (0.1, 0.067), (5, 5.8), (10, 16.6), (20, 53.2), (100, 1066)],
)
async def test_wind_penalty(gust, expected):
    assert await wind_penalty(gust) == pytest.approx(expected)


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [-1, None, "windy"])
async def test_wind_penalty_rejects_invalid_values(value):
    with pytest.raises((TypeError, ValueError)):
        await wind_penalty(value)
