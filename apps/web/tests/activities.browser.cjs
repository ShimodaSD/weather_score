const assert = require('node:assert/strict')
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')

async function main() {
  const browser = await chromium.launch({ headless: true })
  try {
    const page = await browser.newPage()
    await page.clock.install({ time: new Date('2026-09-24T12:00:00') })
    const activity = { activity_id: '1', name: 'Morning run', activity_type: 'running', started_at: '2026-09-24T06:00:00', elapsed_seconds: 3600 }
    for (const key of ['moving_seconds', 'distance_km', 'average_pace_seconds_per_km', 'average_speed_kph', 'average_heart_rate_bpm', 'maximum_heart_rate_bpm', 'calories', 'average_cadence_per_minute', 'elevation_gain_m', 'elevation_loss_m', 'average_temperature_c', 'training_effect', 'anaerobic_training_effect']) activity[key] = null
    let listSize = 1
    let trainingWeeks = 0
    let syncs = 0
    let restoredTss = 100
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
    let progressRequests = 0
    let downloadProgress = { phase: 'downloading', downloaded_files: 2, total_files: 6 }
    await page.route('**/api/**', async (route) => {
      const path = new URL(route.request().url()).pathname
      let data
      if (path.endsWith('/session')) data = { authenticated: true }
      else if (path.endsWith('/activities/sync/status')) { progressRequests++; data = downloadProgress }
      else if (path.endsWith('/activities/sync')) {
        assert.equal(route.request().method(), 'POST')
        syncs++
        downloadProgress = { phase: 'downloading', downloaded_files: 2, total_files: 6 }
        if (syncs > 1) {
          downloadProgress = { phase: 'failed', downloaded_files: 0, total_files: null }
          return route.fulfill({ status: 503, json: { detail: 'Sync failed' } })
        }
        await new Promise((resolve) => { releaseSync = resolve })
        downloadProgress = { phase: 'complete', downloaded_files: 6, total_files: 6 }
        data = { new_activities: 1, total_activities: 2 }
      } else if (path.endsWith('/activities/index')) {
        indexes++
        data = Array.from({ length: listSize }, (_, index) => ({ ...activity, activity_id: String(index + 1), ...(listSize === 100 ? { activity_type: ['running', 'cycling', 'walking', 'running'][index % 4], started_at: index < 4 ? activity.started_at : index === 4 ? '2026-09-27T06:00:00' : index === 5 ? '2026-09-28T06:00:00' : '2026-09-20T06:00:00', distance_km: [5, 20, 50, null][index % 4] } : {}) }))
      } else if (path.endsWith('/profile')) {
        data = { name: 'Runner', threshold_heart_rate_bpm: 157 }
      } else if (path.endsWith('/activities/1')) {
        data = { ...activity, activity: {}, laps: [], splits: [], records: Array.from({ length: 501 }, (_, index) => ({ timestamp: new Date(Date.parse(activity.started_at) + index * 1000).toISOString(), hr: 150, speed: index === 0 ? 0 : index === 1 ? 6 : 10 })), devices: [] }
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
      } else if (path.endsWith('/training/weekly')) {
        trainingWeeks++
        data = Array.from({ length: 12 }, (_, index) => {
          const start = new Date('2026-07-06T12:00:00Z')
          start.setUTCDate(start.getUTCDate() + index * 7)
          const end = new Date(start)
          end.setUTCDate(end.getUTCDate() + 6)
          return { week_start: start.toISOString().slice(0, 10), week_end: end.toISOString().slice(0, 10), tss: syncs ? 120 : restoredTss, threshold_heart_rate_bpm: 157, scored_activity_count: 2, excluded_activity_count: 0, running_km: 10, cycling_km: 30 }
        })
      } else if (path.endsWith('/tss/weekly')) {
        weeks++
        data = { week_start: '2026-09-21', week_end: '2026-09-27', tss: syncs ? 120 : restoredTss, threshold_heart_rate_bpm: 157, scored_activity_count: 2, excluded_activity_count: 0 }
      } else return route.fulfill({ status: 422, json: { detail: 'No heart rate recorded' } })
      await route.fulfill({ json: data })
    })
    await page.goto(`${process.env.WEB_URL || 'http://localhost:8001'}/#activities`)
    await page.getByText('2 of 6 files downloaded · 4 remaining', { exact: true }).waitFor()
    assert.equal(await page.getByRole('button', { name: 'Syncing…' }).isDisabled(), true)
    assert.equal(await page.getByRole('progressbar', { name: 'Garmin files downloaded' }).getAttribute('value'), '2')
    await page.reload()
    await page.getByText('2 of 6 files downloaded · 4 remaining', { exact: true }).waitFor()
    await page.getByRole('link', { name: 'Route grades', exact: true }).click()
    await page.locator('main.grades-page .grade-list').waitFor()
    await page.getByText('2 of 6 files downloaded · 4 remaining', { exact: true }).waitFor()
    assert.equal(await page.getByRole('button', { name: 'Syncing…' }).isDisabled(), true)
    assert.equal(syncs, 0)
    await page.clock.pauseAt(await page.evaluate(() => Date.now() + 1000))
    const gradesBeforeRestore = { indexes, grades }
    listSize = 2
    processing = false
    downloadProgress = { phase: 'complete', downloaded_files: 6, total_files: 6 }
    await page.clock.fastForward(30_000)
    await page.getByText('2 Garmin activities ready to grade.', { exact: true }).waitFor()
    assert.ok(indexes > gradesBeforeRestore.indexes && grades > gradesBeforeRestore.grades)
    const gradesAfterRestore = { indexes, grades }
    const repeatedComplete = page.waitForResponse('**/activities/sync/status')
    await page.clock.fastForward(30_000)
    await repeatedComplete
    assert.deepEqual({ indexes, grades }, gradesAfterRestore)
    await page.clock.resume()
    processing = true
    await page.getByRole('link', { name: 'Activities', exact: true }).click()
    await page.getByRole('button', { name: 'Get new data' }).waitFor()
    assert.equal(await page.getByRole('progressbar', { name: 'Garmin files downloaded' }).count(), 0)
    const grade = page.getByRole('region', { name: 'Activity grade', exact: true })
    await grade.getByText('Grade: processing…', { exact: true }).waitFor()
    processing = false
    await grade.getByText('Grade: 87 / 100', { exact: true }).waitFor()
    assert.equal(await grade.getByRole('link').count(), 0)
    assert.equal(await page.getByRole('link', { name: 'Edit your threshold in Profile' }).count(), 0)
    await page.locator('.activity-row').getByText('Grade: 87 / 100').waitFor()
    downloadProgress = { phase: 'downloading', downloaded_files: 2, total_files: 6 }
    await page.reload()
    await page.getByText('2 of 6 files downloaded · 4 remaining', { exact: true }).waitFor()
    await grade.getByText('Grade: 87 / 100', { exact: true }).waitFor()
    await page.getByLabel('Current week TSS').getByText('100.0', { exact: true }).waitFor()
    await page.clock.pauseAt(await page.evaluate(() => Date.now() + 1000))
    const dashboardBeforeRestore = { weeks, trainingWeeks, indexes, summaries, grades }
    listSize = 3
    restoredTss = 110
    downloadProgress = { phase: 'complete', downloaded_files: 6, total_files: 6 }
    await page.clock.fastForward(30_000)
    await page.getByLabel('Current week TSS').getByText('110.0', { exact: true }).waitFor()
    await grade.getByText('Grade: 87 / 100', { exact: true }).waitFor()
    assert.equal(await page.locator('.activity-row').count(), 3)
    assert.ok(trainingWeeks > dashboardBeforeRestore.trainingWeeks
      && indexes > dashboardBeforeRestore.indexes && summaries > dashboardBeforeRestore.summaries && grades > dashboardBeforeRestore.grades)
    assert.equal(weeks, 0)
    assert.equal(syncs, 0)
    const dashboardAfterRestore = { weeks, trainingWeeks, indexes, summaries, grades }
    const unchangedComplete = page.waitForResponse('**/activities/sync/status')
    await page.clock.fastForward(30_000)
    await unchangedComplete
    assert.deepEqual({ weeks, trainingWeeks, indexes, summaries, grades }, dashboardAfterRestore)
    await page.clock.resume()
    const before = { weeks, trainingWeeks, indexes, summaries, grades }
    await page.setViewportSize({ width: 375, height: 900 })
    await page.waitForFunction(() => document.documentElement.scrollWidth <= innerWidth)
    await page.clock.pauseAt(await page.evaluate(() => Date.now() + 1000))
    await page.getByRole('button', { name: 'Get new data' }).click()
    assert.equal(await page.getByRole('button', { name: 'Syncing…' }).isDisabled(), true)
    const progress = page.getByRole('status').filter({ hasText: 'Updating your Garmin activities' })
    assert.equal(await progress.isVisible(), true)
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
    await page.emulateMedia({ reducedMotion: 'reduce' })
    assert.equal(await page.locator('.activity-sync-spinner').evaluate((element) => getComputedStyle(element).animationName), 'none')
    assert.equal(syncs, 1)
    await page.getByText('2 of 6 files downloaded · 4 remaining', { exact: true }).waitFor()
    const fileProgress = page.getByRole('progressbar', { name: 'Garmin files downloaded' })
    assert.equal(await fileProgress.getAttribute('value'), '2')
    assert.equal(await fileProgress.getAttribute('max'), '6')
    downloadProgress = { phase: 'importing', downloaded_files: 6, total_files: 6 }
    const initialProgressRequests = progressRequests
    await page.clock.fastForward(29_000)
    assert.equal(progressRequests, initialProgressRequests)
    await page.clock.fastForward(1000)
    await page.getByText('6 files downloaded. Importing activities…', { exact: true }).waitFor()
    assert.equal(await fileProgress.getAttribute('value'), null)
    assert.equal(progressRequests, initialProgressRequests + 1)
    await page.clock.resume()
    releaseSync()
    await page.getByText('1 new Garmin activity imported.', { exact: true }).waitFor()
    assert.equal(await progress.count(), 0)
    await page.getByLabel('Current week TSS').getByText('120.0', { exact: true }).waitFor()
    await grade.getByText('Grade: 87 / 100', { exact: true }).waitFor()
    assert.deepEqual({ indexes, summaries, grades }, { indexes: before.indexes + 1, summaries: before.summaries + 1, grades: before.grades + 1 })
    assert.ok(trainingWeeks > before.trainingWeeks)
    assert.equal(weeks, 0)
    await page.getByRole('button', { name: 'Get new data' }).click()
    await page.getByRole('alert').filter({ hasText: 'Sync failed' }).waitFor()
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
      await page.waitForFunction(() => document.documentElement.scrollWidth <= innerWidth)
    }
    hasGrade = false
    await page.reload()
    await grade.getByText('Not graded yet', { exact: true }).waitFor()
    const labelBounds = await grade.getByRole('heading').boundingBox()
    const buttonBounds = await grade.getByRole('button', { name: 'Generate grade', exact: true }).boundingBox()
    assert.ok(buttonBounds.x >= labelBounds.x + labelBounds.width || buttonBounds.y >= labelBounds.y + labelBounds.height)
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
    await page.setViewportSize({ width: 1440, height: 900 })
    listSize = 100
    await page.reload()
    await page.getByRole('link', { name: 'View full activity details' }).waitFor()
    const panels = await page.evaluate(() => ({ list: document.querySelector('.activity-list').clientHeight, detail: document.querySelector('.activity-detail').clientHeight, height: document.querySelector('.activity-rows').clientHeight, scroll: document.querySelector('.activity-rows').scrollHeight }))
    assert.equal(panels.list, panels.detail)
    assert.ok(panels.scroll > panels.height)
    const distanceCard = page.getByLabel('This week’s running and cycling distance', { exact: true })
    assert.equal(await distanceCard.locator('strong').innerText(), '30.0 km')
    assert.ok(await distanceCard.getByText('1 activity without distance excluded').isVisible())
    const chartPanel = page.getByRole('region', { name: 'Weekly distance & TSS' })
    await chartPanel.locator('canvas').waitFor()
    assert.equal(await page.locator('.activity-dashboard > .weekly-training').count(), 1)
    const chartBounds = await chartPanel.boundingBox()
    const gridBounds = await page.locator('.dashboard-grid').boundingBox()
    const totalsBounds = await page.getByRole('region', { name: 'Activity totals' }).boundingBox()
    assert.ok(chartBounds.y >= totalsBounds.y + totalsBounds.height)
    assert.ok(chartBounds.y + chartBounds.height <= gridBounds.y)

    await page.locator('.skip-link').focus()
    await page.keyboard.press('Enter')
    assert.equal(new URL(page.url()).hash, '#activities')
    assert.equal(await page.locator(':focus').getAttribute('id'), 'main')
    await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Profile' }).click()
    await page.getByRole('heading', { name: 'Profile', exact: true }).waitFor()
    assert.equal(await page.locator('.header [aria-current="page"]').innerText(), 'Profile')
    assert.match(await page.title(), /Profile/)
    assert.equal(await page.locator(':focus').textContent(), 'Profile')
    for (const width of [1440, 768, 375, 667]) {
      await page.setViewportSize({ width, height: width === 667 ? 375 : 900 })
      await page.goto(`${process.env.WEB_URL || 'http://localhost:8001'}/#check`)
      await page.getByRole('heading', { level: 1 }).waitFor()
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Conditions overflow at ${width}`)
      const nav = page.getByRole('navigation', { name: 'Main navigation' })
      assert.ok(await nav.getByRole('link', { name: 'Predictions' }).isVisible())
      assert.ok(await nav.getByRole('link', { name: 'Profile' }).isVisible())
      if (width === 375) assert.equal(await page.locator('#address').evaluate((element) => getComputedStyle(element).fontSize), '16px')
    }
    await page.goto(`${process.env.WEB_URL || 'http://localhost:8001'}/#activity?aid=1`)
    const heartRate = page.getByRole('checkbox', { name: 'Heart rate (solid)' })
    await heartRate.waitFor()
    await heartRate.focus()
    await page.keyboard.press('Space')
    assert.equal(await heartRate.isChecked(), false)
    await page.keyboard.press('Space')
    assert.equal(await heartRate.isChecked(), true)
    await page.getByText('View heart rate and pace data', { exact: true }).click()
    await page.locator('.chart-data-table tbody tr').first().waitFor()
    assert.equal(await page.locator('.chart-data-table tbody tr').count(), 500)
    assert.equal(await page.locator('.chart-data-table tbody td').first().innerText(), '150')
    assert.equal(await page.locator('.chart-data-table tbody tr').nth(0).locator('td').nth(1).innerText(), '—')
    assert.equal(await page.locator('.chart-data-table tbody tr').nth(1).locator('td').nth(1).innerText(), '10:00 /km')
    await page.getByRole('button', { name: 'Next' }).click()
    assert.equal(await page.locator('.chart-data-table tbody tr').count(), 1)
    console.log('Activities sync, grade polling, keyboard navigation, responsive and chart checks passed.')
  } finally { await browser.close() }
}

main().catch((error) => { console.error(error); process.exitCode = 1 })
