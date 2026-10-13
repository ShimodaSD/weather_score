const assert = require('node:assert/strict')
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')

async function main() {
  const browser = await chromium.launch({ headless: true })
  try {
    const page = await browser.newPage()
    const activity = { activity_id: '1', name: 'Morning run', activity_type: 'running', started_at: '2026-09-24T06:00:00', elapsed_seconds: 3600 }
    for (const key of ['moving_seconds', 'distance_km', 'average_pace_seconds_per_km', 'average_speed_kph', 'average_heart_rate_bpm', 'maximum_heart_rate_bpm', 'calories', 'average_cadence_per_minute', 'elevation_gain_m', 'elevation_loss_m', 'average_temperature_c', 'training_effect', 'anaerobic_training_effect']) activity[key] = null
    let syncs = 0
    let weeks = 0
    let indexes = 0
    let summaries = 0
    let grades = 0
    let processing = true
    let hasGrade = true
    let gradeStarts = 0
    let releaseGrade
    let failGrades = false
    let releaseSync
    await page.route('**/api/**', async (route) => {
      const path = new URL(route.request().url()).pathname
      let data
      if (path.endsWith('/session')) data = { authenticated: true }
      else if (path.endsWith('/activities/sync')) {
        assert.equal(route.request().method(), 'POST')
        syncs++
        if (syncs > 1) return route.fulfill({ status: 503, json: { detail: 'Sync failed' } })
        await new Promise((resolve) => { releaseSync = resolve })
        data = { new_activities: 1, total_activities: 2 }
      } else if (path.endsWith('/activities/index')) {
        indexes++
        data = [activity]
      } else if (path.endsWith('/summary')) {
        summaries++
        data = activity
      } else if (path.endsWith('/activities/1/grade')) {
        assert.equal(route.request().method(), 'POST')
        gradeStarts++
        if (gradeStarts > 1) return route.fulfill({ status: 503, json: {} })
        await new Promise((resolve) => { releaseGrade = resolve })
        hasGrade = true
        processing = true
        data = { activity_id: '1', status: 'processing', score: null, segments: [], error: null, created_at: activity.started_at, updated_at: activity.started_at, completed_at: null }
      } else if (path.endsWith('/activities/grades')) {
        grades++
        if (failGrades) return route.fulfill({ status: 503, json: {} })
        data = [{ activity_id: '1', status: processing ? 'processing' : 'complete', score: processing ? null : 87, segments: [], error: null, created_at: activity.started_at, updated_at: activity.started_at, completed_at: null }]
        if (!hasGrade) data = []
      } else if (path.endsWith('/tss/weekly')) {
        weeks++
        data = { week_start: '2026-09-21', week_end: '2026-09-27', tss: syncs ? 120 : 100, threshold_heart_rate_bpm: 157, scored_activity_count: 2, excluded_activity_count: 0 }
      } else return route.fulfill({ status: 422, json: { detail: 'No heart rate recorded' } })
      await route.fulfill({ json: data })
    })
    await page.goto(`${process.env.WEB_URL || 'http://localhost:8001'}/#activities`)
    const grade = page.getByRole('region', { name: 'Activity grade', exact: true })
    await grade.getByText('Grade: processing…', { exact: true }).waitFor()
    processing = false
    await grade.getByText('Grade: 87 / 100', { exact: true }).waitFor()
    assert.equal(await grade.getByRole('link').count(), 0)
    assert.equal(await page.getByRole('link', { name: 'Edit your threshold in Profile' }).count(), 0)
    await page.locator('.activity-row').getByText('Grade: 87 / 100').waitFor()
    const before = { weeks, indexes, summaries, grades }
    await page.getByRole('button', { name: 'Get new data' }).click()
    assert.equal(await page.getByRole('button', { name: 'Syncing…' }).isDisabled(), true)
    const progress = page.getByRole('status').filter({ hasText: 'Updating your Garmin activities' })
    assert.equal(await progress.isVisible(), true)
    await page.setViewportSize({ width: 375, height: 900 })
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
    await page.emulateMedia({ reducedMotion: 'reduce' })
    assert.equal(await page.locator('.activity-sync-spinner').evaluate((element) => getComputedStyle(element).animationName), 'none')
    assert.equal(syncs, 1)
    releaseSync()
    await page.getByText('1 new Garmin activity imported.', { exact: true }).waitFor()
    assert.equal(await progress.count(), 0)
    await page.getByLabel('Current week TSS').getByText('120.0', { exact: true }).waitFor()
    await grade.getByText('Grade: 87 / 100', { exact: true }).waitFor()
    assert.ok(weeks > before.weeks && indexes > before.indexes && summaries > before.summaries && grades > before.grades)
    await page.getByRole('button', { name: 'Get new data' }).click()
    await page.getByRole('alert').filter({ hasText: 'Activities are unavailable' }).waitFor()
    const messageBounds = await page.locator('.activity-dashboard > .error-message').boundingBox()
    const dataBounds = await page.getByRole('region', { name: 'Activity totals' }).boundingBox()
    assert.ok(dataBounds.y - (messageBounds.y + messageBounds.height) >= 24)
    assert.equal(await page.getByRole('button', { name: 'Get new data' }).isEnabled(), true)
    failGrades = true
    await page.reload()
    await page.getByRole('button', { name: 'Retry grades' }).waitFor()
    failGrades = false
    await page.getByRole('button', { name: 'Retry grades' }).click()
    await grade.getByText('Grade: 87 / 100', { exact: true }).waitFor()
    for (const width of [375, 1440]) {
      await page.setViewportSize({ width, height: 900 })
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
    }
    hasGrade = false
    await page.reload()
    await grade.getByText('Not graded yet', { exact: true }).waitFor()
    const labelBounds = await grade.getByRole('heading').boundingBox()
    const buttonBounds = await grade.getByRole('button', { name: 'Generate grade', exact: true }).boundingBox()
    assert.ok(buttonBounds.x >= labelBounds.x + labelBounds.width)
    await grade.getByRole('button', { name: 'Generate grade', exact: true }).click()
    assert.equal(await grade.getByRole('button', { name: 'Starting…' }).isDisabled(), true)
    assert.equal(gradeStarts, 1)
    releaseGrade()
    await grade.getByRole('button', { name: 'Processing…' }).waitFor()
    assert.equal(await grade.getByRole('button', { name: 'Processing…' }).isDisabled(), true)
    processing = false
    await grade.getByText('Grade: 87 / 100', { exact: true }).waitFor()
    await grade.getByRole('button', { name: 'Regenerate grade' }).click()
    await grade.getByRole('alert').waitFor()
    assert.equal(await grade.getByRole('button', { name: 'Regenerate grade' }).isEnabled(), true)
    activity.activity_type = 'cycling'
    hasGrade = false
    await page.reload()
    await grade.getByRole('button', { name: 'Running only' }).waitFor()
    assert.equal(await grade.getByRole('button', { name: 'Running only' }).isDisabled(), true)
    console.log('Activities sync, refresh, grade polling, retry and responsive checks passed.')
  } finally { await browser.close() }
}

main().catch((error) => { console.error(error); process.exitCode = 1 })
