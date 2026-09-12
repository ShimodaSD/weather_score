import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import { fetchAccessToken, fetchRunGrade } from './api.ts'

const grade = JSON.parse(readFileSync(new URL('../../../tests/contracts/run_grade.json', import.meta.url), 'utf8'))

test('sign-in exchanges credentials for an in-memory bearer token', async (t) => {
  const mock = t.mock.method(globalThis, 'fetch', async () => new Response('{"access_token":"token","token_type":"bearer"}'))
  assert.equal(await fetchAccessToken('/api/', 'runner', 'secret'), 'token')
  assert.equal(mock.mock.calls[0].arguments[0], '/api/token')
  assert.equal(mock.mock.calls[0].arguments[1]?.method, 'POST')
  assert.equal(String(mock.mock.calls[0].arguments[1]?.body), 'username=runner&password=secret')
  mock.mock.mockImplementation(async () => new Response('', { status: 401 }))
  await assert.rejects(fetchAccessToken('/api', 'runner', 'wrong'), /Incorrect username or password/)
  await assert.rejects(fetchAccessToken('/api', '', 'secret'), /Enter your username/)
})

test('grade client accepts the API response contract and selected locations', async (t) => {
  const mock = t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify(grade)))
  assert.deepEqual(await fetchRunGrade('/api/', ' Brisbane & surrounds ', '5:20', 'token'), grade)
  assert.equal(mock.mock.calls[0].arguments[0], '/api/grade/run?address=Brisbane+%26+surrounds')
  assert.equal(mock.mock.calls[0].arguments[1]?.method, 'POST')
  assert.equal(new Headers(mock.mock.calls[0].arguments[1]?.headers).get('Authorization'), 'Bearer token')
  assert.equal(mock.mock.calls[0].arguments[1]?.body, '{"average_pace_minutes_per_km":"5:20"}')
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
