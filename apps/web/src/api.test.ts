import assert from 'node:assert/strict'
import { test } from 'node:test'
import { fetchRunningScore } from './api.ts'

test('running score client validates responses and handles service failures', async (t) => {
  const mock = t.mock.method(globalThis, 'fetch', async () => new Response('82.5'))
  assert.equal(await fetchRunningScore('/api/', ' Brisbane & surrounds '), 82.5)
  assert.equal(mock.mock.calls[0].arguments[0], '/api/score/run?address=Brisbane+%26+surrounds')
  for (const score of [0, 100]) {
    mock.mock.mockImplementation(async () => new Response(String(score)))
    assert.equal(await fetchRunningScore('/api', 'Brisbane'), score)
  }
  for (const payload of ['-1', '101', 'null', '"85"', '{}', 'not json']) {
    mock.mock.mockImplementation(async () => new Response(payload))
    await assert.rejects(fetchRunningScore('/api', 'Brisbane'), /unexpected response/)
  }
  mock.mock.mockImplementation(async () => new Response('{"error":"not found"}'))
  await assert.rejects(fetchRunningScore('/api', 'Unknown'), /couldn’t find/)
  mock.mock.mockImplementation(async () => new Response('', { status: 502 }))
  await assert.rejects(fetchRunningScore('/api', 'Brisbane'), /unavailable/)
  mock.mock.mockImplementation(async () => new Response('', { status: 401 }))
  await assert.rejects(fetchRunningScore('/api', 'Brisbane'), /authentication/)
  mock.mock.mockImplementation(async () => { throw new TypeError('Failed to fetch') })
  await assert.rejects(fetchRunningScore('/api', 'Brisbane'), /couldn’t reach/)
  await assert.rejects(fetchRunningScore('/api', '  '), /Enter a town/)
})
