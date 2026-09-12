# Activity API

All endpoints require the configured bearer token.

- `GET /activities/index` returns every activity's `activity_id`, `started_at`,
  `activity_type`, and `name`, newest first. It reads only the main activities
  table for fast dashboard selection.
- `GET /activities?activity_type=running&limit=50` returns recent summaries.
- `GET /activities/{activity_id}/summary` returns only the main statistics for
  one ID, without loading laps or per-sample records.
- `GET /activities/{activity_id}` returns the same summary fields plus every
  directly linked GarminDB row: `activity`, sport-specific activity data,
  `laps`, `splits`, `records`, `activity_devices`, `devices`, `device_info`,
  and `files`. Missing sport-specific data is `null`; missing collections are
  empty arrays. Unknown IDs return 404.
- `GET /activities/running/predictions` returns 5, 10, 21, and 42 km time
  estimates or bounded ranges, the recorded benchmark efforts used, the count
  of usable recent runs, and the longest run. It reads only running distance,
  moving time, start time, and ID; it does not load per-sample records.

The summary uses kilometres, seconds, km/h, bpm, metres, and Celsius as named.
Average pace and speed are derived from moving time and distance because the
imported `avg_speed` field can be empty. Raw fields retain GarminDB's names,
units, and timestamp representation. Detail responses can be large: they
include every per-sample record, including location coordinates when stored.

The detail page charts record heart rate (`hr`) and converts positive record
speed from km/h to pace in minutes/km as `60 / speed`. The pace axis includes
the supplied zones through 9:00/km and extends to show faster samples at
their calculated pace. Zona 6 includes every pace faster than 4:10/km.
Slower, stopped, and missing-speed samples are shown at 9:00/km. Shaded bands
use the Trote and Zona 0–6 ranges shown in the UI, and the chart tooltip
names the matching zone. The horizontal axis measures elapsed minutes from
the activity start and ends at the activity's elapsed duration when record
timestamps are present.

The dashed climb-adjusted line estimates flat-equivalent speed from positive
altitude gain within a rolling 100 m distance window. It uses
`adjusted_speed_kph = speed_kph × (1 + 10 × uphill_metres / horizontal_metres)`
and plots `60 / adjusted_speed_kph` on the pace axis so it can be compared with
recorded pace. At least 50 m of valid distance and altitude samples are needed;
missing altitude or speed leaves a gap. This is a simple uphill adjustment,
not a physiological grade-adjusted pace model; downhill does not add a credit.

Vertical bars mark the end of each lap on the same elapsed-minutes axis. The
marker time is lap `start_time` plus `elapsed_time`; imported `stop_time` is not
used because it can be at or before the lap start.

Running predictions use the long-duration branch of the
[Emig–Peltonen performance model](https://www.nature.com/articles/s41467-020-18737-6):
`distance = v_m × time × (1 − γ_l × ln(time / 360 s))`.
The API examines the latest 180-day window of recorded runs and selects the
fastest moving time within ±3% of 5 km, 10 km, 21.0975 km, and 42.195 km.
At least two consistent benchmark distances are needed to fit personal aerobic
power `v_m` and endurance `γ_l`. Fits outside the study's bounds (`2 < v_m < 7`
m/s, `0.039 < γ_l < 0.135`) or with more than 5% mean relative time error are
rejected.

When no personal fit is possible but one benchmark exists, the API anchors the
model to the longest benchmark and solves the equation at both published `γ_l`
bounds. It returns a range, not a point prediction. These bounds are a
parameter envelope, not a statistical confidence interval. When no benchmark
exists, no times are returned. Using training activity moving times rather
than confirmed maximal race efforts is a local adaptation, so the paper's
reported race-prediction accuracy must not be applied to these estimates.
