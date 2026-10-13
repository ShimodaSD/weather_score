# Activity Training Stress Score

The Activities dashboard's selected-activity panel and the full activity
detail page automatically display a heart-rate-zone TSS estimate.
The protected `GET /activities/{activity_id}/tss` endpoint performs the
calculation using the saved profile when no query inputs are supplied.
The browser displays the result without calculation inputs or a submit button.
Explicit pace/power query inputs remain supported for API clients.
No new dependencies or background jobs are needed. Scores are calculated on
demand; the profile's name and threshold are persisted.

## Heart-rate threshold

The initial profile threshold is **157 bpm**, as requested by the user.
Change it on the authenticated **Profile** page (`#profile`), where name is
also editable. This is a personal setting, not a universal threshold or a
change to an external training account. Returning to an activity reloads TSS
with the saved value, including for historical activities; threshold history
is not stored. Missing heart-rate data is shown as unavailable, not zero.

`GET /profile` returns `{ "name": null, "threshold_heart_rate_bpm": 157 }`
initially. `PUT /profile` requires a trimmed name of 1–100 characters and an
integer threshold of 30–250 bpm. Both require the existing bearer token or
browser session. The application's database contains `athlete_profile` with
`id`, `name`, `threshold_heart_rate_bpm`, and `updated_at`. A primary key and
`CHECK (id = 1)` restrict it to the single account supported by current auth.
Database constraints also validate name length and threshold range. Table
creation and default insertion are idempotent and never overwrite a saved
profile. Name starts null so the user can enter it; no name is guessed.
Saving atomically upserts both editable fields. Add account ownership if auth
is changed to support multiple users.

`heart_rate_estimate` uses Joe Friel's published
[average-HR estimation table](https://www.trainingpeaks.com/learn/articles/estimating-training-stress-score-tss/)
and [sport-specific threshold zones](https://www.trainingpeaks.com/learn/articles/joe-friel-s-quick-guide-to-setting-zones/).
Estimate = elapsed hours × zone load per hour. For zones 1, 2, 3, 4, 5a, 5b,
5c, rates are 30, 55, 70, 80, 100, 120, 140. Zone 1 uses the middle published
rate; zone 2 uses the midpoint of the published low/high rates because the
summary cannot distinguish those subdivisions. These are coaching estimates,
not an additional peer-reviewed formula or the proprietary hrTSS algorithm.

Running zone lower bounds are 85%, 90%, 95%, 100%, 103% of threshold;
cycling uses 81%, 90%, 94%, 100%, 103%. Above 106% is zone 5c. Fractional
percentages between printed whole-number ranges remain in the lower zone.
The response's intensity factor is the HR/threshold ratio for information;
it is not squared to compute the heart-rate estimate.

Recorded average HR and elapsed duration are required; missing HR is never
zero-filled or replaced with pace. Elapsed time includes pauses and can
overestimate load. Average HR also hides intervals and is affected by drift.
Rates do not infer resting or maximum HR. Values outside 30–250 bpm and
mixed heart-rate/pace/power inputs are rejected. At 157 bpm, one hour with
average HR of 157 yields 100 estimated TSS.

## Formula and provenance

For cycling, use the established Coggan/TrainingPeaks formulation reproduced
in papers [1–3]:

```text
IF = normalized_power_watts / ftp_watts
TSS = (duration_seconds × normalized_power_watts × IF)
      / (ftp_watts × 3600) × 100
    = duration_seconds / 3600 × IF² × 100
```

One hour at FTP gives 100; two hours gives 200; one hour at half FTP gives 25.
TSS is accumulated training load, not the application's 0–100 weather grade.
It is non-negative and has no upper cap. Only the final TSS is rounded to two
decimal places. Higher values do not mean better conditions or better fitness.

Normalized power reflects variable effort, conventionally using fourth-power
weighting of 30-second rolling mean power. This feature accepts already
calculated NP; it does not substitute average power or reconstruct NP from
incomplete records. The inspected GarminDB `activities` and `cycle_activities`
schemas do not contain NP or FTP. Therefore the rider supplies NP, FTP valid
on the activity date, and matching timer duration. Timer time includes
zero-power coasting and excludes pauses; moving time is unsuitable for a
stationary trainer. Elapsed time is not silently substituted.

For running, the implementation makes an explicit local approximation to the
duration/relative-intensity structure discussed in [1, 4, 5]:

```text
average_speed_mps = distance_km × 1000 / moving_seconds
threshold_speed_mps = 1000 / threshold_pace_seconds_per_km
IF = average_speed_mps / threshold_speed_mps
   = distance_km × threshold_pace_seconds_per_km / moving_seconds
estimated_TSS = moving_seconds / 3600 × IF² × 100
```

The pace ratio must be inverted: faster running increases IF. Recorded
distance and moving time are used without rounding intermediate pace.
Threshold pace must come from the athlete, for the activity date; it is not
inferred from this activity or from the fastest training run.

This is **not validated rTSS** or an implementation of TrainingPeaks' normalized
graded pace algorithm. Mean speed loses interval structure and does not
adjust hills, surface, wind, heat, or recovery stops. The UI and API always
identify it as `running_pace_estimate`. The existing chart's uphill heuristic
is not used as physiological grade-adjusted pace. These five papers inform
the formula, calibration and limitations; they do not independently validate
this local average-pace approximation.

## Five research sources

1. **Kontro, Mastracci, Cheung & MacInnis (2026).** *The three-dimensional
   impulse-response model: Modeling the training process in accordance with
   energy system-specific adaptation*. PLOS ONE 21(2), e0341721.
   [Paper, equation 1](https://doi.org/10.1371/journal.pone.0341721).
   Supplies the NP/FTP equation and 100-point threshold-hour anchor. Its
   critique supports treating TSS as a load index rather than a recovery or
   adaptation prediction, particularly for intermittent and above-threshold work.
2. **de Groot et al. (2018).** *Relationship between internal and external
   handcycle training load in people with spinal cord injury training for the
   HandbikeBattle*. Journal of Rehabilitation Medicine.
   [Paper, training-load methods](https://doi.org/10.2340/16501977-2316).
   Describes individual threshold calibration and the 100-point hour. Its HTML
   equation prints `FTP/3600` in the denominator, inconsistent with that anchor;
   we use `FTP × 3600`, consistent with [1] and dimensional normalization.
   Its handcycling population does not validate a running estimator.
3. **Woods et al. (2018).** *The effects of intensified training on resting
   metabolic rate (RMR), body composition and performance in trained cyclists*.
   PLOS ONE 13(2), e0191644.
   [Paper, training-load methods](https://doi.org/10.1371/journal.pone.0191644).
   Uses duration/intensity load anchored to individual FTP and 100 TSS/hour.
   Supports a personal threshold input rather than a population default.
4. **Wallace, Slattery & Coutts (2014).** *A comparison of methods for
   quantifying training load: relationships between modelled and actual
   training responses*. European Journal of Applied Physiology 114, 11–20.
   [Author manuscript](https://opus.lib.uts.edu.au/rest/bitstreams/e2dda996-4443-4fc3-8643-997dfae38c17/retrieve).
   Evaluates running training stress alongside session-RPE and TRIMP. Supports
   considering sport-specific relative intensity; its findings must not be
   attributed to our unadjusted average-speed proxy.
5. **Wells, Hoffmann, Bruce, Kremer & Dwyer (2026).** *Training load and
   intensity in triathlon: objective differences between sex, age, race distance
   preference and training phase across a cohort of 95 age-group triathletes
   over six months*. Frontiers in Sports and Active Living 8, 1798702.
   [Paper, table 1](https://doi.org/10.3389/fspor.2026.1798702).
   Lists sport-specific TSS variants and emphasizes accurate thresholds and
   training dose rather than measured stress response. The running table's
   pace notation is ambiguous: this implementation explicitly uses a speed
   ratio so faster pace raises load. Cross-sport scores are not assumed to
   produce equivalent adaptations.

## API and validation

The dashboard's **This week's TSS** card calls protected
`GET /activities/tss/weekly?week_of=YYYY-MM-DD`, supplying today's local browser
calendar date (not its UTC date). Weeks run Monday through Sunday. The database
query includes activity start times from Monday midnight up to, but excluding,
the next Monday, using GarminDB's stored timezone-less calendar timestamps.
Activities crossing midnight are assigned wholly to the week in which they
started. No activity-list filter, pagination limit, or per-activity request
changes the total. Returning from Profile reloads it with the saved threshold.

The backend sums the same rounded heart-rate estimates shown on activity
details. It returns dates, threshold, scored count and excluded count. Missing
or invalid HR/duration and unsupported sports are excluded and disclosed as a
partial total. An empty week returns 0; a week containing only unscorable
activities returns null and is shown as unavailable. Fetch errors have a retry
action and are never shown as zero. This remains estimated training load.

Running example:
`GET /activities/123/tss?threshold_pace_seconds_per_km=300`.

Cycling example:
`GET /activities/123/tss?ftp_watts=250&normalized_power_watts=250&duration_seconds=7200`.

Both require the existing bearer token or authenticated browser session. The
stored activity determines the sport. Unknown IDs return 404; unsupported
sports, missing data, mismatched sport inputs, zero duration/thresholds,
negative or non-finite values, and numerical overflow return 422. Explicit
zero NP is valid and produces zero load. Missing NP never becomes zero.
The response includes method, duration, intensity, threshold, unit, IF and
limitations. No weather-provider requests occur. Profile reads initialize the
table/default row if absent; calculations do not persist scores.

The shared cycling contract is `tests/contracts/activity_tss.json`. Calculation
tests cover threshold, low-intensity, above-threshold, longer-duration, zero
power, missing, invalid and extreme inputs. API tests verify authentication,
recorded data, error statuses and the shared contract. Frontend client tests
verify that contract, units, credentials, validation and errors.

`ponytail:` Average running speed is a deliberate ceiling. Replace this proxy
with a separately validated terrain/interval-aware method when reliable
streams and the required validation are available; retain method provenance.
