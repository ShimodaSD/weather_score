import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

import { SESSION_AUTH, endSession, fetchAccessToken, fetchActivityDetail, fetchActivityGrades, fetchActivityIndex, fetchActivitySummary, fetchActivityTss, fetchWeeklyTss, fetchWeeklyTraining, fetchProfile, saveProfile, fetchRunGrade, fetchRunScore, fetchRunningPredictions, hasSession, startActivityGrade, syncGarminActivities, fetchGarminSyncProgress } from './api.ts'


const grade = JSON.parse(readFileSync(new URL('../../../tests/contracts/run_grade.json', import.meta.url), 'utf8'))

test('weekly TSS uses local calendar date and validates partial, empty and failed totals', async (t) => {
  const result = { week_start: '2026-09-21', week_end: '2026-09-27', tss: 250.5, threshold_heart_rate_bpm: 157, scored_activity_count: 3, excluded_activity_count: 1 }
  const mock = t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify(result)))
  assert.deepEqual(await fetchWeeklyTss('/api/', 'token', new Date(2026, 8, 24, 0, 1)), result)
  assert.equal(mock.mock.calls[0].arguments[0], '/api/activities/tss/weekly?week_of=2026-09-24')
  assert.equal(new Headers(mock.mock.calls[0].arguments[1]?.headers).get('Authorization'), 'Bearer token')
  for (const tss of [0, null]) {
    const empty = { ...result, tss, scored_activity_count: 0 }
    mock.mock.mockImplementation(async () => new Response(JSON.stringify(empty)))
    assert.deepEqual(await fetchWeeklyTss('/api', SESSION_AUTH), empty)
  }
  for (const invalid of [{}, { ...result, tss: -1 }, { ...result, scored_activity_count: 1.5 }, { ...result, week_start: 'invalid' }, { ...result, threshold_heart_rate_bpm: 0 }]) {
    mock.mock.mockImplementation(async () => new Response(JSON.stringify(invalid)))
    await assert.rejects(fetchWeeklyTss('/api', 'token'), /unexpected weekly TSS/)
  }
  mock.mock.mockImplementation(async () => new Response('', { status: 503 }))
  await assert.rejects(fetchWeeklyTss('/api', 'token'), /unavailable/)
})

test('profile client loads defaults and saves name and threshold with authentication', async (t) => {
  const initial = { name: null, threshold_heart_rate_bpm: 157 }
  const mock = t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify(initial)))
  assert.deepEqual(await fetchProfile('/api', 'token'), initial)
  assert.equal(mock.mock.calls[0].arguments[0], '/api/profile')
  const updated = { name: 'Runner', threshold_heart_rate_bpm: 170 }
  mock.mock.mockImplementation(async () => new Response(JSON.stringify(updated)))
  assert.deepEqual(await saveProfile('/api', SESSION_AUTH, { ...updated, name: ' Runner ' }), updated)
  const options = mock.mock.calls.at(-1)?.arguments[1]
  assert.equal(options?.method, 'PUT')
  assert.equal(options?.credentials, 'include')
  assert.equal(new Headers(options?.headers).get('Content-Type'), 'application/json')
  assert.deepEqual(JSON.parse(String(options?.body)), updated)
  await assert.rejects(saveProfile('/api', 'token', { ...updated, name: ' ' }), /Enter your name/)
  await assert.rejects(saveProfile('/api', 'token', { ...updated, threshold_heart_rate_bpm: 251 }), /whole-number threshold/)
  mock.mock.mockImplementation(async () => new Response('{"name":null,"threshold_heart_rate_bpm":0}'))
  await assert.rejects(fetchProfile('/api', 'token'), /unexpected profile/)
  mock.mock.mockImplementation(async () => new Response('', { status: 500 }))
  await assert.rejects(saveProfile('/api', 'token', updated), /unavailable/)
})

test('TSS client checks the shared contract and sends thresholds with authentication', async (t) => {
  const result = JSON.parse(readFileSync(new URL('../../../tests/contracts/activity_tss.json', import.meta.url), 'utf8'))
  const mock = t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify(result)))
  const inputs = { ftp_watts: 250, normalized_power_watts: 250, duration_seconds: 7200 }
  assert.deepEqual(await fetchActivityTss('/api/', '123', 'token', inputs), result)
  assert.equal(mock.mock.calls[0].arguments[0], '/api/activities/123/tss?ftp_watts=250&normalized_power_watts=250&duration_seconds=7200')
  assert.equal(new Headers(mock.mock.calls[0].arguments[1]?.headers).get('Authorization'), 'Bearer token')
  assert.equal(mock.mock.calls[0].arguments[1]?.credentials, 'include')
  const run = { ...result, method: 'running_pace_estimate', intensity_unit: 'm/s' }
  mock.mock.mockImplementation(async () => new Response(JSON.stringify(run)))
  assert.deepEqual(await fetchActivityTss('/api', '123', SESSION_AUTH, { threshold_pace_seconds_per_km: 300 }), run)
  assert.equal(mock.mock.calls.at(-1)?.arguments[0], '/api/activities/123/tss?threshold_pace_seconds_per_km=300')
  assert.equal(new Headers(mock.mock.calls.at(-1)?.arguments[1]?.headers).has('Authorization'), false)
  const heartRate = { ...result, method: 'heart_rate_estimate', intensity_unit: 'bpm', threshold: 157 }
  mock.mock.mockImplementation(async () => new Response(JSON.stringify(heartRate)))
  assert.deepEqual(await fetchActivityTss('/api', '123', 'token', { threshold_heart_rate_bpm: 157 }), heartRate)
  assert.equal(mock.mock.calls.at(-1)?.arguments[0], '/api/activities/123/tss?threshold_heart_rate_bpm=157')
  assert.deepEqual(await fetchActivityTss('/api', '123', 'token'), heartRate)
  assert.equal(mock.mock.calls.at(-1)?.arguments[0], '/api/activities/123/tss')
  for (const invalid of [{}, { ...result, tss: -1 }, { ...result, threshold: 0 },
    { ...result, duration_seconds: 0 }, { ...result, warnings: null },
    { ...result, intensity_unit: 'm/s' }, { ...result, activity_id: 'other' }]) {
    mock.mock.mockImplementation(async () => new Response(JSON.stringify(invalid)))
    await assert.rejects(fetchActivityTss('/api', '123', 'token', inputs), /unexpected TSS/)
  }
  mock.mock.mockImplementation(async () => new Response('{"detail":"Recorded distance is required."}', { status: 422 }))
  await assert.rejects(fetchActivityTss('/api', '123', 'token', inputs), /Recorded distance is required/)
  mock.mock.mockImplementation(async () => new Response('', { status: 401 }))
  await assert.rejects(fetchActivityTss('/api', '123', 'token', inputs), /sign-in expired/)
  await assert.rejects(fetchActivityTss('/api', '123', 'token', { threshold_pace_seconds_per_km: NaN }), /valid positive/)
})

test('sign-in requests a browser session cookie', async (t) => {
  const mock = t.mock.method(globalThis, 'fetch', async () => new Response('{"access_token":"token","token_type":"bearer"}'))
  assert.equal(await fetchAccessToken('/api/', 'runner', 'secret'), 'token')
  assert.equal(mock.mock.calls[0].arguments[0], '/api/token')
  assert.equal(mock.mock.calls[0].arguments[1]?.method, 'POST')
  assert.equal(mock.mock.calls[0].arguments[1]?.credentials, 'include')
  assert.equal(String(mock.mock.calls[0].arguments[1]?.body), 'username=runner&password=secret')
  mock.mock.mockImplementation(async () => new Response('', { status: 401 }))
  await assert.rejects(fetchAccessToken('/api', 'runner', 'wrong'), /Incorrect username or password/)
  await assert.rejects(fetchAccessToken('/api', '', 'secret'), /Enter your username/)
})

test('browser session restores and signs out with cookie credentials', async (t) => {
  const mock = t.mock.method(globalThis, 'fetch', async () => new Response('{"authenticated":true}'))
  assert.equal(await hasSession('/api/'), true)
  assert.equal(mock.mock.calls[0].arguments[0], '/api/session')
  assert.equal(mock.mock.calls[0].arguments[1]?.credentials, 'include')
  mock.mock.mockImplementation(async () => new Response('', { status: 401 }))
  assert.equal(await hasSession('/api'), false)
  mock.mock.mockImplementation(async () => new Response(null, { status: 204 }))
  await endSession('/api')
  assert.equal(mock.mock.calls[2].arguments[0], '/api/logout')
  assert.equal(mock.mock.calls[2].arguments[1]?.credentials, 'include')
  assert.equal(mock.mock.calls[2].arguments[1]?.method, 'POST')
})

test('grade client accepts the API response contract and selected locations', async (t) => {
  const mock = t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify(grade)))
  assert.deepEqual(await fetchRunGrade('/api/', ' Brisbane & surrounds ', '5:20'), grade)
  assert.equal(mock.mock.calls[0].arguments[0], '/api/grade/run?address=Brisbane+%26+surrounds')
  assert.equal(mock.mock.calls[0].arguments[1]?.method, 'POST')
  assert.equal(new Headers(mock.mock.calls[0].arguments[1]?.headers).has('Authorization'), false)
  assert.equal(mock.mock.calls[0].arguments[1]?.body, '{"average_pace_minutes_per_km":"5:20"}')
  await fetchRunGrade('/api', 'Brisbane', '5:20')
  const option = { name: 'Springfield, Victoria', latitude: '-37.41', longitude: '144.82' }
  mock.mock.mockImplementation(async () => new Response(JSON.stringify({ options: [option] })))
  assert.deepEqual(await fetchRunGrade('/api', 'Springfield', '5:20'), [option])
  mock.mock.mockImplementation(async () => new Response(JSON.stringify(grade)))
  assert.deepEqual(await fetchRunGrade('/api', 'Springfield', '5:20', option), grade)
  assert.equal(mock.mock.calls.at(-1)?.arguments[0], '/api/grade/run?address=Springfield&latitude=-37.41&longitude=144.82')
})

test('grade client rejects invalid or failed responses', async (t) => {
  const mock = t.mock.method(globalThis, 'fetch', async () => new Response('{}'))
  for (const payload of ['{}', '82.5', '{"score":101}', 'not json']) {
    mock.mock.mockImplementation(async () => new Response(payload))
    await assert.rejects(fetchRunGrade('/api', 'Brisbane', '5:20'), /unexpected response/)
  }
  mock.mock.mockImplementation(async () => new Response('{"error":"not found"}'))
  await assert.rejects(fetchRunGrade('/api', 'Unknown', '5:20'), /couldn’t find/)
  mock.mock.mockImplementation(async () => new Response('', { status: 502 }))
  await assert.rejects(fetchRunGrade('/api', 'Brisbane', '5:20'), /unavailable/)
  mock.mock.mockImplementation(async () => { throw new TypeError('Failed to fetch') })
  await assert.rejects(fetchRunGrade('/api', 'Brisbane', '5:20'), /couldn’t reach/)
  await assert.rejects(fetchRunGrade('/api', ' ', '5:20'), /Enter a town/)
  await assert.rejects(fetchRunGrade('/api', 'Brisbane', 'bad pace'), /Enter a pace/)
})

test('weather score client accepts score and selected locations', async (t) => {
  const mock = t.mock.method(globalThis, 'fetch', async () => new Response('84.5'))
  assert.equal(await fetchRunScore('/api', ' Brisbane '), 84.5)
  assert.equal(mock.mock.calls[0].arguments[0], '/api/score/run?address=Brisbane')
  const location = { name: 'Springfield', latitude: '-37.41', longitude: '144.82' }
  mock.mock.mockImplementation(async () => new Response(JSON.stringify({ options: [location] })))
  assert.deepEqual(await fetchRunScore('/api', 'Springfield'), [location])
  mock.mock.mockImplementation(async () => new Response('84.5'))
  assert.equal(await fetchRunScore('/api', 'Springfield', location), 84.5)
  assert.equal(mock.mock.calls.at(-1)?.arguments[0], '/api/score/run?address=Springfield&latitude=-37.41&longitude=144.82')
})

test('activity index and detail use protected, validated endpoints', async (t) => {
  const index = { activity_id: '123', activity_type: 'running', name: 'Morning Run', started_at: '2026-09-11T06:30:00Z' }
  const summary = { ...index, elapsed_seconds: 1800, moving_seconds: 1740, distance_km: 5,
    average_pace_seconds_per_km: 348, average_speed_kph: 10.3, average_heart_rate_bpm: 150,
    maximum_heart_rate_bpm: 170, calories: 400, average_cadence_per_minute: 174,
    elevation_gain_m: 30, elevation_loss_m: 28, average_temperature_c: 22,
    training_effect: 3.2, anaerobic_training_effect: 0.5 }
  const detail = { ...summary, activity: { sport: 'running' }, laps: [{ lap: 1 }], splits: [], records: [{ hr: 150 }], devices: [] }
  const mock = t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify([index])))
  assert.deepEqual(await fetchActivityIndex('/api/', 'token'), [index])
  assert.equal(mock.mock.calls[0].arguments[0], '/api/activities/index')
  assert.equal(new Headers(mock.mock.calls[0].arguments[1]?.headers).get('Authorization'), 'Bearer token')
  mock.mock.mockImplementation(async () => new Response(JSON.stringify(summary)))
  assert.deepEqual(await fetchActivitySummary('/api', '123', 'token'), summary)
  assert.equal(mock.mock.calls[1].arguments[0], '/api/activities/123/summary')
  mock.mock.mockImplementation(async () => new Response(JSON.stringify(detail)))
  assert.deepEqual(await fetchActivityDetail('/api', '123', 'token'), detail)
  assert.equal(mock.mock.calls[2].arguments[0], '/api/activities/123')
  mock.mock.mockImplementation(async () => new Response('{}'))
  await assert.rejects(fetchActivityDetail('/api', '123', 'token'), /unexpected activity response/)
  mock.mock.mockImplementation(async () => new Response(JSON.stringify({ ...detail, devices: [null] })))
  await assert.rejects(fetchActivityDetail('/api', '123', 'token'), /unexpected activity response/)
  mock.mock.mockImplementation(async () => new Response('', { status: 404 }))
  await assert.rejects(fetchActivityDetail('/api', 'missing', 'token'), /Activity not found/)
})

test('running predictions use the protected summary endpoint', async (t) => {
  const data = { run_count: 1, longest_run_km: 10, season_start_at: '2026-03-15T06:30:00Z',
    season_end_at: '2026-09-11T06:30:00Z', model_status: 'range', vm_mps: null,
    endurance_index: null, basis: [{ distance_km: 10, moving_seconds: 3000,
      source_activity_id: '123', source_distance_km: 10, source_started_at: '2026-09-11T06:30:00Z' }],
    predictions: [{ distance_km: 5, predicted_seconds: null, low_seconds: 1400, high_seconds: 1600 }] }
  const mock = t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify(data)))
  assert.deepEqual(await fetchRunningPredictions('/api', 'token'), data)
  assert.equal(mock.mock.calls[0].arguments[0], '/api/activities/running/predictions')
  assert.equal(new Headers(mock.mock.calls[0].arguments[1]?.headers).get('Authorization'), 'Bearer token')
  mock.mock.mockImplementation(async () => new Response(JSON.stringify({ ...data, predictions: [{}] })))
  await assert.rejects(fetchRunningPredictions('/api', 'token'), /unexpected prediction response/)
})

test('activity grades list and start through protected endpoints', async (t) => {
  const data = { activity_id: '123', status: 'processing', score: null, segments: [], error: null,
    created_at: '2026-09-17T00:00:00Z', updated_at: '2026-09-17T00:00:00Z', completed_at: null }
  const mock = t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify([data])))
  assert.deepEqual(await fetchActivityGrades('/api', 'token'), [data])
  assert.equal(mock.mock.calls[0].arguments[0], '/api/activities/grades')
  mock.mock.mockImplementation(async () => new Response(JSON.stringify(data)))
  assert.deepEqual(await startActivityGrade('/api', '123', 'token'), data)
  assert.equal(mock.mock.calls[1].arguments[0], '/api/activities/123/grade')
  assert.equal(mock.mock.calls[1].arguments[1]?.method, 'POST')
  mock.mock.mockImplementation(async () => new Response(JSON.stringify({ ...data, status: 'unknown' })))
  await assert.rejects(fetchActivityGrades('/api', 'token'), /unexpected grade response/)
})

test('Garmin sync uses the protected incremental sync endpoint', async (t) => {
  const result = { new_activities: 1, total_activities: 42 }
  const mock = t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify(result)))

  assert.deepEqual(await syncGarminActivities('/api', 'token'), result)
  assert.equal(mock.mock.calls[0].arguments[0], '/api/activities/sync')
  assert.equal(mock.mock.calls[0].arguments[1]?.method, 'POST')
  assert.equal(new Headers(mock.mock.calls[0].arguments[1]?.headers).get('Authorization'), 'Bearer token')
})


test('weekly training validates distances and sends the local date with auth', async (t) => {
  const week = { week_start: '2026-09-21', week_end: '2026-09-27', tss: 80, threshold_heart_rate_bpm: 157, scored_activity_count: 2, excluded_activity_count: 0, running_km: 5, cycling_km: 25 }
  const weeks = Array.from({ length: 12 }, () => ({ ...week }))
  const mock = t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify(weeks)))
  assert.deepEqual(await fetchWeeklyTraining('/api', 'token', new Date(2026, 8, 24)), weeks)
  assert.equal(mock.mock.calls[0].arguments[0], '/api/activities/training/weekly?week_of=2026-09-24')
  assert.equal(new Headers(mock.mock.calls[0].arguments[1]?.headers).get('Authorization'), 'Bearer token')
  for (const invalid of [[], weeks.map((week) => ({ ...week, running_km: -1 })), weeks.map((week) => ({ ...week, cycling_km: '25' })), weeks.map((week) => ({ ...week, tss: -1 }))]) {
    mock.mock.mockImplementation(async () => new Response(JSON.stringify(invalid)))
    await assert.rejects(fetchWeeklyTraining('/api', 'token'), /unexpected weekly training/)
  }
  mock.mock.mockImplementation(async () => new Response(JSON.stringify(weeks.map((week) => ({ ...week, running_km: null, tss: null })))))
  assert.equal((await fetchWeeklyTraining('/api', 'token'))[0].running_km, null)
})


test('activity requests display first-import setup guidance', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify({ detail: 'Garmin activity data is not initialized. Use Get new data to run the first import.' }), { status: 503 }))
  await assert.rejects(fetchActivityIndex('/api', 'token'), /Use Get new data/)
  await assert.rejects(fetchWeeklyTraining('/api', 'token'), /Use Get new data/)
})


test('activity index accepts recorded distances and rejects invalid distances', async (t) => {
  const item = { activity_id: '1', activity_type: 'running', name: null, started_at: '2026-09-11T06:30:00Z', distance_km: 5.5 }
  const mock = t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify([item])))
  assert.equal((await fetchActivityIndex('/api', 'token'))[0].distance_km, 5.5)
  for (const distance_km of [-1, '5', false]) {
    mock.mock.mockImplementation(async () => new Response(JSON.stringify([{ ...item, distance_km }])))
    await assert.rejects(fetchActivityIndex('/api', 'token'), /unexpected activity response/)
  }
})


test('Garmin progress validates counters and uses authentication', async (t) => {
  const result = { phase: 'downloading', downloaded_files: 2, total_files: 6 }
  const mock = t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify(result)))
  assert.deepEqual(await fetchGarminSyncProgress('/api', 'token'), result)
  assert.equal(mock.mock.calls[0].arguments[0], '/api/activities/sync/status')
  assert.equal(new Headers(mock.mock.calls[0].arguments[1]?.headers).get('Authorization'), 'Bearer token')
  for (const invalid of [{ ...result, downloaded_files: -1 }, { ...result, total_files: 1 }, { ...result, phase: 'unknown' }, {}]) {
    mock.mock.mockImplementation(async () => new Response(JSON.stringify(invalid)))
    await assert.rejects(fetchGarminSyncProgress('/api', 'token'), /unexpected Garmin download progress/)
  }
  mock.mock.mockImplementation(async () => new Response('', { status: 401 }))
  await assert.rejects(fetchGarminSyncProgress('/api', 'token'), /sign-in expired/)
})
