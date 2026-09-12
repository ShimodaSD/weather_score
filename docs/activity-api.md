# Activity API

All endpoints require the configured bearer token.

- `GET /activities?activity_type=running&limit=50` returns recent summaries.
- `GET /activities/{activity_id}/summary` returns only the main statistics for
  one ID, without loading laps or per-sample records.
- `GET /activities/{activity_id}` returns the same summary fields plus every
  directly linked GarminDB row: `activity`, sport-specific activity data,
  `laps`, `splits`, `records`, `activity_devices`, `devices`, `device_info`,
  and `files`. Missing sport-specific data is `null`; missing collections are
  empty arrays. Unknown IDs return 404.

The summary uses kilometres, seconds, km/h, bpm, metres, and Celsius as named.
Average pace and speed are derived from moving time and distance because the
imported `avg_speed` field can be empty. Raw fields retain GarminDB's names,
units, and timestamp representation. Detail responses can be large: they
include every per-sample record, including location coordinates when stored.
