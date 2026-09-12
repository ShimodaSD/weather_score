# Pace-aware run grade

`POST /grade/run?address=Brisbane` produces a suitability index for the
current conditions at the supplied address. It grades conditions rather than
the runner's ability.

## Request

```json
{
  "average_pace_minutes_per_km": "5:20"
}
```

Pace strings use `minutes:seconds` notation, with seconds between `00` and
`59`. Decimal minutes, such as `5.333`, are also accepted.

The API geocodes the query-string address and retrieves the current weather.
WeatherAPI's gust speed is treated conservatively as a headwind, and its wet
bulb temperature is used as the thermal input. Client-supplied weather fields
are rejected. The endpoint remains bearer-token protected.

If geocoding finds several places, the response contains `options`. Send the
selected option's coordinates as `latitude` and `longitude` query parameters
with the same request body to grade that place without geocoding again. Both
coordinates are required together. The web page signs in through `POST /token`
and keeps the bearer token only in memory.

## Equations and evidence

Every arithmetic operation performed by the scoring engine is documented
below. The equations use unrounded intermediate values. Rounding happens only
when the response is created.

### Symbols and units

| Symbol | Request or intermediate value | Unit |
| --- | --- | --- |
| `p` | average pace | s/km |
| `w` | signed route-relative wind; positive is a headwind | km/h |
| `B` | wet-bulb globe temperature (WBGT) | degrees Celsius |
| `v` | runner speed | m/s |
| `a` | air speed relative to the runner | m/s |
| `a_ref` | reference air speed from the wind study | m/s |
| `W` | estimated wind-related metabolic change | percentage points |
| `T` | estimated thermal performance loss | percentage points |

The conversions between km/h and m/s use the factor documented by the
[NIST Guide to the SI](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b9):

```text
1 km/h = 1 / 3.6 m/s
1 m/s  = 3.6 km/h
```

### 1. Convert pace to running speed

A pace of `p` seconds to cover 1,000 metres gives:

```text
v = 1000 / p
```

The value returned as `running_speed_kph` is:

```text
running_speed_kph = 3.6 * v
```

These are dimensional unit conversions, not empirical models.

### 2. Calculate relative air speed

First convert the signed wind component to m/s, then add it to running speed:

```text
w_mps = w / 3.6
a = max(0, v + w_mps)
```

The zero floor prevents a tailwind faster than the runner from producing a
negative relative air speed. The response converts the result back to km/h:

```text
relative_air_speed_kph = 3.6 * a
```

### 3. Derive the wind coefficients

[Yamashita et al. (2024)](https://journals.physiology.org/doi/10.1152/japplphysiol.00159.2024)
modelled the oxygen requirement of running as linear with squared relative air
speed. The paper reports a 2.2% increase for the headwind created by running at
21.5 km/h and a 3.1% decrease for the equivalent tailwind case. The engine
uses those values to derive separate headwind and tailwind coefficients:

```text
a_ref = 21.5 / 3.6
k_head = 2.2 / a_ref^2
k_tail = 3.1 / a_ref^2
```

Numerically, `a_ref` is approximately 5.9722 m/s, `k_head` is approximately
0.06168 percentage points per (m/s)^2, and `k_tail` is approximately 0.08691
percentage points per (m/s)^2.

### 4. Calculate wind-related metabolic change

The engine applies the study-derived coefficients to the difference in squared
air speed. It selects the branch from the sign of the request's route-relative
wind component:

```text
if w >= 0:
    W = k_head * (a^2 - v^2)
else:
    W = -k_tail * (v^2 - a^2)
```

A headwind normally makes `W` positive and a tailwind makes it negative. The
value is returned as `wind_metabolic_change_percent`.

### 5. Calculate thermal performance loss

[Mantzios et al. (2022)](https://pubmed.ncbi.nlm.nih.gov/34652333/)
found peak marathon performance at 7.5 degrees Celsius WBGT and reported
performance losses of 0.2% per degree above and 0.1% per degree below that
point. The equivalent piecewise equation used by the engine is:

```text
if B >= 7.5:
    T = (B - 7.5) * 0.2
else:
    T = (7.5 - B) * 0.1
```

It can also be written as one equation:

```text
T = 0.2 * max(B - 7.5, 0) + 0.1 * max(7.5 - B, 0)
```

The value is returned as `thermal_performance_loss_percent`.

### 6. Combine and bound the score

Only adverse wind change reduces suitability. A negative `W` records a
tailwind benefit but does not increase the score above 100:

```text
raw_score = 100 - T - max(0, W)
score = max(0, min(100, raw_score))
```

This is equivalently `clamp(raw_score, 0, 100)`. Combining the independently
estimated wind and thermal percentage effects by subtraction, treating them
as score points, and bounding the result are application-level design choices.
Neither paper validates this combined score as an individualized outcome.

### 7. Round response values

Each response number is rounded independently to two decimal places after all
calculations:

```text
response_value = round(unrounded_value, 2)
```

## Research limitations

The wind study included walking and running trials; this implementation uses
only its running-specific result. The thermal study included running and
racewalking events; this implementation uses its marathon-specific optimum and
slopes. The wind study tested 14 active adults and relative air speeds up to
6 m/s. Results outside the studied populations and ranges are extrapolations.
The grade is not medical advice or an individualized race prediction.

## Sources

- Yamashita N, et al. [*Air speed and direction affect metabolic and
  thermoregulatory responses during walking and running in a temperate
  environment*](https://doi.org/10.1152/japplphysiol.00159.2024). Journal of
  Applied Physiology. 2024.
- Mantzios K, et al. [*Effects of Weather Parameters on Endurance Running
  Performance: Discipline-specific Analysis of 1258
  Races*](https://doi.org/10.1249/MSS.0000000000002769). Medicine & Science in
  Sports & Exercise. 2022. [PubMed
  record](https://pubmed.ncbi.nlm.nih.gov/34652333/).
- National Institute of Standards and Technology. [*NIST Guide to the SI,
  Appendix B.9: Factors for Units Listed by Kind of Quantity or Field of
  Science*](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b9).
