# Data to provide for better running predictions

Start with two recent race results at different distances and your last 12 weeks
of running history. Identify which activities were races or maximal time trials.
These provide a clearer picture of current performance than unlabelled training
runs alone.

This document describes data to collect and possible improvements. The current
predictor does not yet consume the additional fields described below.

## What the application does today

The predictor reads activity ID, start date, distance in kilometres, and moving
time in seconds. Within the 180 days ending at the latest recorded run, it
selects the fastest moving time within ±3% of each benchmark distance: 5 km,
10 km, 21.0975 km, and 42.195 km.

It fits the Emig–Peltonen endurance model when at least two benchmark distances
pass its consistency checks. Otherwise, one benchmark produces a range based
on fixed endurance bounds; no benchmark produces no predictions. The current
output targets are 5, 10, 21, and 42 km, so the last two are not exact official
half-marathon and marathon distances.

The predictor does not distinguish races from easy runs, account for pauses
through elapsed time, or use training volume, heart rate, weather, or terrain.
Its window ends at the latest recorded activity rather than today's date, so
old imports can produce estimates based on old fitness. See
[the API documentation](activity-api.md) and
[the implementation](../src/weather_score/application/running_predictions.py).

## What to provide, in priority order

| Priority | Data | How to provide it | Purpose and current gap |
|---|---|---|---|
| 1 | Two recent races or maximal time trials at different distances | Activity ID, date, exact distance, official elapsed time, race/time-trial label, and whether the effort was maximal | Gives performance benchmarks instead of assuming every fast training run represents race ability. Two distinct distances support a personal endurance fit. |
| 2 | Recent running history | Last 12 weeks of activities, including date, distance, duration, and workout type; include weeks with no running | Allows weekly distance, frequency, training pace, and interval/tempo work to be assessed. These currently do not influence predictions. |
| 3 | Target race | Exact distance, race date, location, and local start time | Defines the event and distinguishes current ability from a forecast of future fitness. The current model has no target date. |
| 4 | Conditions for benchmark efforts and the target race | Location and start time for historical weather; temperature in °C when known; route elevation and road/trail/treadmill label | Helps identify efforts affected by heat or a different course. Conditions currently do not affect predicted times. Temperature has direct support in the cited marathon research; terrain is useful context without a validated correction in this application. |
| 5 | Optional profile information | Age, sex, height in cm, and weight in kg | These may support an alternative statistical model. They are not required by the current endurance model. |

The 12-week history is a practical collection window, not a validated requirement
of the existing formula. Prefer benchmarks from the same recent training period;
record illness, injury, or substantial training interruptions that make older
results less representative. Do not perform a new maximal test solely to fill
in this document; existing race results are useful starting points.

## What Garmin can supply and what you need to confirm

Activity dates, distances, moving times, and activity IDs already reach the
predictor. Training totals can be derived from the imported activity history
without asking you to type weekly totals.

You should confirm which activities were races or maximal efforts, supply
official results when available, and identify your target event. Elapsed time,
workout labels, GPS/elevation, and heart-rate availability should be checked in
the imported data before requesting separate exports. Do not share Garmin
passwords or access tokens.

Official elapsed time should be retained separately from moving time: a race
clock includes stops, while a watch may remove them. Use the official event
distance when available and retain GPS distance separately. Do not treat a
paused training run as equivalent to a continuous race.

## Fill-in template

Copy this template once for the target event and once per benchmark effort.
Use `unknown` for missing values rather than zero.

```text
Target event
  Name:
  Distance (km):
  Date:
  Location and local start time:
  Surface and course elevation, if known:

Benchmark effort
  Activity ID or official result reference:
  Date:
  Type: race / maximal time trial / training
  Official distance (km), if available:
  GPS distance (km), if available:
  Official elapsed time (hh:mm:ss), if available:
  Watch elapsed time (hh:mm:ss):
  Watch moving time (hh:mm:ss):
  Maximal effort: yes / no / unknown
  Location and local start time:
  Temperature (°C), if known:
  Surface, elevation, pauses, or other relevant context:

Training history
  Activities covering the last 12 weeks:
  Workout labels: easy / long run / tempo / intervals / race / unknown
  Missing weeks or activities:
  Significant illness, injury, or training interruptions:
```

## Research sources to consult

Search PubMed for relevant studies, including articles from these journals:

- Sports Medicine
- British Journal of Sports Medicine (BJSM)
- Medicine & Science in Sports & Exercise (MSSE)
- International Journal of Sports Physiology and Performance (IJSPP)
- Journal of Applied Physiology

These are sources for further research; the specific studies supporting the
current recommendations are listed below.

## Research behind these priorities

1. **Performance across distances:** Emig and Peltonen studied approximately
   14,000 runners and 1.6 million sessions using aerobic power and endurance
   parameters. This is the framework used here, but our benchmark selection is
   a local adaptation. Its published accuracy cannot be assumed for our use of
   unconfirmed training efforts.
   [Human running performance from real-world big data (2020), PMID 33024098](https://pubmed.ncbi.nlm.nih.gov/33024098/).
2. **Prior races and training context:** A study of 2,303 recreational runners
   found associations between performance and weekly mileage, training type,
   age, sex, and BMI. Models using prior races improved marathon predictions
   compared with the Riegel formula. This supports evaluating these inputs;
   it does not prove they will improve our current model.
   [An empirical study of race times in recreational endurance runners (2016), PMID 27570626](https://pubmed.ncbi.nlm.nih.gov/27570626/).
3. **Temperature:** An analysis of approximately 1.8 million marathon
   performances identified temperature as the strongest environmental factor
   examined. It supports collecting temperature, but does not establish an
   individual correction for every distance or runner.
   [Impact of environmental parameters on marathon running performance (2012), PMID 22649525](https://pubmed.ncbi.nlm.nih.gov/22649525/).

## How to establish whether predictions improve

First improve benchmark identification and time definitions. Then evaluate
training context and condition adjustments against the current model using
later race results that were not used to fit or select the model. Only data
available before each race should enter its prediction.

Report absolute time error, percentage error, and the number and distances of
held-out races. More input fields alone do not establish better predictions.
The current fallback ranges are parameter envelopes, not statistical confidence
intervals, and a fitted point estimate still has uncertainty.
