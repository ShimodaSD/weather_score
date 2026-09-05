import pytest

from weather_score.application.main import rain_penalty


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "precipitation, expected",
    [(0, 0), (1, 0.33), (10, 3.3), (15, 4.95), (15.15151515151515, 5), (16, 5), (1000, 5)],
)
async def test_rain_penalty(precipitation, expected):
    assert await rain_penalty(precipitation) == pytest.approx(expected)


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [-1, None, "rain"])
async def test_rain_penalty_rejects_invalid_values(value):
    with pytest.raises((TypeError, ValueError)):
        await rain_penalty(value)
