import pytest

from weather_score.application.main import altitude_penalty


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "altitude, expected",
    [(0, 0), (300, 0), (500, 0), (501, 0.003), (1000, 1.5), (9000, 25.5)],
)
async def test_altitude_penalty(altitude, expected):
    assert await altitude_penalty(altitude) == pytest.approx(expected)


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [None, "high", float("inf")])
async def test_altitude_penalty_rejects_invalid_values(value):
    with pytest.raises((TypeError, ValueError)):
        await altitude_penalty(value)
