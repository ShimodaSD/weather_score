import assert from 'node:assert/strict'
import { test } from 'node:test'
import { buildActivitySeries, buildLapMarkers, MAX_PACE_MIN_PER_KM, MIN_PACE_MIN_PER_KM, PACE_ZONES, paceZoneName } from './activityChart.ts'

test('activity chart aligns BPM, caps slow pace, and preserves pace faster than Zona 6', () => {
  const series = buildActivitySeries([
    { timestamp: '2026-09-11T06:30:00Z', hr: 150, speed: 12 },
    { timestamp: '2026-09-11T06:31:00Z', hr: 155, speed: 0 },
    { timestamp: '2026-09-11T06:32:00Z', hr: null, speed: 10 },
  ], '2026-09-11T06:30:00Z')
  assert.equal(series.xUnit, 'minutes')
  assert.deepEqual(series.heartRate, [{ x: 0, y: 150 }, { x: 1, y: 155 }, { x: 2, y: null }])
  assert.deepEqual(series.pace, [{ x: 0, y: 5 }, { x: 1, y: 9 }, { x: 2, y: 6 }])
  assert.equal(MAX_PACE_MIN_PER_KM, 9)
  assert.equal(MIN_PACE_MIN_PER_KM, 3.75)
  assert.deepEqual(buildActivitySeries([{ speed: 7.5 }, { speed: 6 }, { speed: 20 }, {}, { speed: null }], '2026-09-11T06:30:00Z').pace,
    [{ x: 0, y: 8 }, { x: 1, y: 9 }, { x: 2, y: 3 }, { x: 3, y: 9 }, { x: 4, y: 9 }])
  assert.deepEqual(PACE_ZONES.map(({ name, fastSeconds, slowSeconds }) => [name, fastSeconds, slowSeconds]), [
    ['Trote', 450, 540], ['Zona 0', 386, 450], ['Zona 1', 346, 386], ['Zona 2', 307, 346],
    ['Zona 3', 284, 307], ['Zona 4', 270, 284], ['Zona 5', 250, 270], ['Zona 6', 225, 250],
  ])
  assert.equal(paceZoneName(5), 'Zona 3')
  assert.equal(paceZoneName(250 / 60), 'Zona 5')
  assert.equal(paceZoneName(249 / 60), 'Zona 6')
  assert.equal(paceZoneName(3.75), 'Zona 6')
  assert.equal(paceZoneName(3), 'Zona 6')
  assert.equal(paceZoneName(9), 'Trote or slower / no speed')
})

test('activity chart positions samples from the activity start, including recording gaps', () => {
  const series = buildActivitySeries([
    { timestamp: '2026-09-11T06:32:00Z', hr: 150, speed: 12 },
    { timestamp: '2026-09-11T06:34:30Z', hr: 155, speed: 10 },
  ], '2026-09-11T06:30:00Z')
  assert.deepEqual(series.heartRate.map(({ x }) => x), [2, 4.5])
  assert.deepEqual(series.pace.map(({ x }) => x), [2, 4.5])
})

test('climb-adjusted pace uses uphill gain over distance and leaves missing data blank', () => {
  const series = buildActivitySeries([
    { distance: 0, altitude: 100, speed: 12 },
    { distance: 0.05, altitude: 102, speed: 12 },
    { distance: 0.1, altitude: 105, speed: 12 },
    { distance: 0.2, altitude: 100, speed: 12 },
    { distance: 0.3, altitude: null, speed: 12 },
    { distance: 0.4, altitude: 100, speed: 0 },
  ], '2026-09-11T06:30:00Z')
  assert.equal(series.adjustedPace[0].y, null)
  assert.ok(Math.abs(series.adjustedPace[1].y! - 60 / 16.8) < 1e-9)
  assert.ok(Math.abs(series.adjustedPace[2].y! - 60 / 18) < 1e-9)
  assert.equal(series.adjustedPace[3].y, 5)
  assert.equal(series.adjustedPace[4].y, null)
  assert.equal(series.adjustedPace[5].y, null)
})

test('lap bars use lap start plus duration, ignoring unusable stop timestamps', () => {
  const start = '2026-09-11T06:30:00Z'
  const markers = buildLapMarkers([
    { lap: 0, start_time: start, stop_time: start, elapsed_time: '00:10:00' },
    { lap: 1, start_time: '2026-09-11T06:40:00Z', stop_time: start, elapsed_time: '00:05:30.500000' },
    { lap: 2, start_time: '2026-09-11T06:45:30Z', elapsed_time: null },
  ], start, 1800)
  assert.deepEqual(markers, [{ x: 10, label: '1' }, { x: 15 + 30.5 / 60, label: '2' }])
})
