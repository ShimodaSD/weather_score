# Pace-aware run grade

`POST /grade/run` produces a suitability index for the supplied wind and
thermal conditions. It grades conditions rather than the runner's ability.

## Request

```json
{
  "average_pace_seconds_per_km": 300,
  "headwind_kph": 12,
  "wet_bulb_globe_temperature_c": 15
}
```

`headwind_kph` is the wind component along the direction of travel. Positive
values are headwinds and negative values are tailwinds. A weather station's
unsigned wind speed must first be resolved against the route direction.

## Equations and evidence

Average pace is converted to running speed, and the signed wind component is
added to get relative air speed. Yamashita et al. (2024) found running oxygen
use to be linear with squared relative air speed. Their reported changes at
21.5 km/h, 2.2% for headwind and -3.1% for tailwind, define the slopes:

```text
headwind change (%) = 2.2 / (21.5 / 3.6)^2 * (relative_speed^2 - run_speed^2)
tailwind change (%) = -3.1 / (21.5 / 3.6)^2 * (run_speed^2 - relative_speed^2)
```

Mantzios et al. (2022) found peak marathon performance at 7.5 degrees Celsius
WBGT and reported performance losses of 0.2% per degree above and 0.1% per
degree below that point:

```text
thermal loss (%) = 0.2 * max(WBGT - 7.5, 0)
                 + 0.1 * max(7.5 - WBGT, 0)
```

The final 0-100 suitability score combines the adverse-condition factors:

```text
score = clamp(100 - thermal_loss - max(wind_change, 0), 0, 100)
```

A tailwind benefit is returned in `wind_metabolic_change_percent`, but does
not raise the score above 100. The factor equations and coefficients come from
the cited studies. Combining the two percentage effects into a bounded score
is an application-level choice and is not validated by either paper as an
individualized outcome.

## Research limitations

The wind study included walking and running trials; this implementation uses
only its running-specific result. The thermal study included running and
racewalking events; this implementation uses its marathon-specific optimum and
slopes. The wind study tested 14 active adults and relative air speeds up to
6 m/s. Results outside the studied populations and ranges are extrapolations.
The grade is not medical advice or an individualized race prediction.

## Sources

- Yamashita N, et al. *Air speed and direction affect metabolic and
  thermoregulatory responses during walking and running in a temperate
  environment.* Journal of Applied Physiology. 2024.
  https://doi.org/10.1152/japplphysiol.00159.2024
- Mantzios K, et al. *Effects of Weather Parameters on Endurance Running
  Performance: Discipline-specific Analysis of 1258 Races.* Medicine &
  Science in Sports & Exercise. 2022.
  https://doi.org/10.1249/MSS.0000000000002769
