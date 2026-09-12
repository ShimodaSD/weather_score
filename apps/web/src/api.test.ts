import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import { SESSION_AUTH, endSession, fetchAccessToken, fetchActivityDetail, fetchActivityIndex, fetchActivitySummary, fetchRunGrade, fetchRunningPredictions, hasSession } from './api.ts'

const grade = JSON.parse(readFileSync(new URL('../../../tests/contracts/run_grade.json', import.meta.url), 'utf8'))

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
  assert.deepEqual(await fetchRunGrade('/api/', ' Brisbane & surrounds ', '5:20', 'token'), grade)
  assert.equal(mock.mock.calls[0].arguments[0], '/api/grade/run?address=Brisbane+%26+surrounds')
  assert.equal(mock.mock.calls[0].arguments[1]?.method, 'POST')
  assert.equal(new Headers(mock.mock.calls[0].arguments[1]?.headers).get('Authorization'), 'Bearer token')
  assert.equal(mock.mock.calls[0].arguments[1]?.body, '{"average_pace_minutes_per_km":"5:20"}')
  await fetchRunGrade('/api', 'Brisbane', '5:20', SESSION_AUTH)
  assert.equal(new Headers(mock.mock.calls[1].arguments[1]?.headers).has('Authorization'), false)
  assert.equal(mock.mock.calls[1].arguments[1]?.credentials, 'include')
  const option = { name: 'Springfield, Victoria', latitude: '-37.41', longitude: '144.82' }
  mock.mock.mockImplementation(async () => new Response(JSON.stringify({ options: [option] })))
  assert.deepEqual(await fetchRunGrade('/api', 'Springfield', '5:20', 'token'), [option])
  mock.mock.mockImplementation(async () => new Response(JSON.stringify(grade)))
  assert.deepEqual(await fetchRunGrade('/api', 'Springfield', '5:20', 'token', option), grade)
  assert.equal(mock.mock.calls.at(-1)?.arguments[0], '/api/grade/run?address=Springfield&latitude=-37.41&longitude=144.82')
})

test('grade client rejects invalid or failed responses', async (t) => {
  const mock = t.mock.method(globalThis, 'fetch', async () => new Response('{}'))
  for (const payload of ['{}', '82.5', '{"score":101}', 'not json']) {
    mock.mock.mockImplementation(async () => new Response(payload))
    await assert.rejects(fetchRunGrade('/api', 'Brisbane', '5:20', 'token'), /unexpected response/)
  }
  mock.mock.mockImplementation(async () => new Response('{"error":"not found"}'))
  await assert.rejects(fetchRunGrade('/api', 'Unknown', '5:20', 'token'), /couldn’t find/)
  mock.mock.mockImplementation(async () => new Response('', { status: 502 }))
  await assert.rejects(fetchRunGrade('/api', 'Brisbane', '5:20', 'token'), /unavailable/)
  mock.mock.mockImplementation(async () => new Response('', { status: 401 }))
  await assert.rejects(fetchRunGrade('/api', 'Brisbane', '5:20', 'token'), /sign-in expired/)
  mock.mock.mockImplementation(async () => { throw new TypeError('Failed to fetch') })
  await assert.rejects(fetchRunGrade('/api', 'Brisbane', '5:20', 'token'), /couldn’t reach/)
  await assert.rejects(fetchRunGrade('/api', ' ', '5:20', 'token'), /Enter a town/)
  await assert.rejects(fetchRunGrade('/api', 'Brisbane', 'bad pace', 'token'), /Enter a pace/)
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
