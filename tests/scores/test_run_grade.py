import pytest

from weather_score.application.run_grade import calculate_run_grade


def grade(**overrides):
    values = {
        "average_pace_seconds_per_km": 300,
        "headwind_kph": 0,
        "wet_bulb_globe_temperature_c": 7.5,
    }
    values.update(overrides)
    return calculate_run_grade(**values)


def test_ideal_conditions_score_one_hundred():
    result = grade()

    assert result.score == 100
    assert result.running_speed_kph == 12
    assert result.relative_air_speed_kph == 12
    assert result.wind_metabolic_change_percent == 0
    assert result.thermal_performance_loss_percent == 0


def test_headwind_uses_pace_to_increase_relative_air_speed():
    faster = grade(average_pace_seconds_per_km=240, headwind_kph=20)
    slower = grade(average_pace_seconds_per_km=360, headwind_kph=20)

    assert faster.relative_air_speed_kph == 35
    assert slower.relative_air_speed_kph == 30
    assert (
        faster.wind_metabolic_change_percent
        > slower.wind_metabolic_change_percent
    )
    assert faster.score < slower.score


def test_tailwind_reports_benefit_without_exceeding_one_hundred():
    result = grade(headwind_kph=-8)

    assert result.wind_metabolic_change_percent < 0
    assert result.score == 100


def test_tailwind_cannot_make_relative_air_speed_negative():
    result = grade(average_pace_seconds_per_km=600, headwind_kph=-20)

    assert result.relative_air_speed_kph == 0


def test_hot_and_cold_boundaries_use_published_slopes():
    hot = grade(wet_bulb_globe_temperature_c=17.5)
    cold = grade(wet_bulb_globe_temperature_c=-2.5)

    assert hot.thermal_performance_loss_percent == 2
    assert cold.thermal_performance_loss_percent == 1


def test_poor_conditions_receive_a_low_grade():
    result = grade(headwind_kph=50, wet_bulb_globe_temperature_c=30)

    assert result.score < 90


def test_extreme_conditions_are_clamped_to_zero():
    result = grade(
        average_pace_seconds_per_km=60,
        headwind_kph=200,
        wet_bulb_globe_temperature_c=60,
    )

    assert result.score == 0


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"average_pace_seconds_per_km": 0}, "greater than zero"),
        ({"average_pace_seconds_per_km": float("nan")}, "pace must be finite"),
        ({"headwind_kph": float("nan")}, "headwind must be finite"),
        ({"wet_bulb_globe_temperature_c": float("nan")}, "WBGT must be finite"),
        ({"wet_bulb_globe_temperature_c": 61}, "WBGT must be between"),
    ],
)
def test_invalid_values_are_rejected(overrides, message):
    with pytest.raises(ValueError, match=message):
        grade(**overrides)
