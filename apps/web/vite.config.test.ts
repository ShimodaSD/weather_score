import assert from 'node:assert/strict'
import { test } from 'node:test'
import { resolveConfig } from 'vite'

test('development forwards grade requests without a personal env file', async () => {
  const config = await resolveConfig({ envFile: false }, 'serve')
  const proxy = config.server.proxy?.['/api']
  assert.ok(proxy && typeof proxy === 'object', 'Missing API proxy would serve the HTML app instead of a grade')
  assert.equal(proxy.target, 'http://127.0.0.1:8000')
  assert.equal(proxy.rewrite?.('/api/grade/run?address=Brisbane'), '/grade/run?address=Brisbane')
})
