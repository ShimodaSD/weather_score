import { useEffect, useRef, useState } from 'react'
import { Chart, BarController, BarElement, CategoryScale, LineController, LineElement, PointElement, LinearScale, Legend, Tooltip } from 'chart.js'
import { fetchWeeklyTraining, type WeeklyTraining } from './api'

Chart.register(BarController, BarElement, CategoryScale, LineController, LineElement, PointElement, LinearScale, Legend, Tooltip)

const weekLabel = (date: string) => new Date(`${date}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

export default function WeeklyTrainingChart({ token, onTokenChange }: { token: string; onTokenChange: (token: string) => void }) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const [weeks, setWeeks] = useState<WeeklyTraining[] | null>(null)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    let cancelled = false
    setWeeks(null)
    setError('')
    fetchWeeklyTraining(import.meta.env.VITE_API_BASE_URL || '/api', token).then((data) => {
      if (!cancelled) setWeeks(data)
    }).catch((reason) => {
      if (cancelled) return
      if (reason instanceof Error && reason.message.includes('sign-in expired')) onTokenChange('')
      setError(reason instanceof Error ? reason.message : 'Could not load weekly training.')
    })
    return () => { cancelled = true }
  }, [token, onTokenChange, retry])

  useEffect(() => {
    if (!canvas.current || !weeks) return
    const colors = getComputedStyle(canvas.current)
    const patternCanvas = document.createElement('canvas')
    patternCanvas.width = patternCanvas.height = 10
    const context = patternCanvas.getContext('2d')!
    context.fillStyle = colors.getPropertyValue('--chart-cycling').trim()
    context.fillRect(0, 0, 10, 10)
    context.strokeStyle = '#fff'
    context.lineWidth = 2
    context.beginPath()
    context.moveTo(0, 10)
    context.lineTo(10, 0)
    context.stroke()
    const cyclingPattern = canvas.current.getContext('2d')!.createPattern(patternCanvas, 'repeat')!
    const chart = new Chart(canvas.current, {
      type: 'bar',
      data: {
        labels: weeks.map((week) => weekLabel(week.week_start)),
        datasets: [
          { type: 'line', label: 'Combined TSS', data: weeks.map((week) => week.tss), yAxisID: 'tss', borderColor: colors.getPropertyValue('--chart-tss').trim(), backgroundColor: colors.getPropertyValue('--chart-tss').trim(), borderDash: [6, 3], pointRadius: 3, order: 0 },
          { label: 'Running (km)', data: weeks.map((week) => week.running_km), backgroundColor: colors.getPropertyValue('--chart-running').trim(), yAxisID: 'km', order: 1 },
          { label: 'Cycling (km)', data: weeks.map((week) => week.cycling_km), backgroundColor: cyclingPattern, yAxisID: 'km', order: 1 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        interaction: { mode: 'index', intersect: false },
        plugins: { legend: { position: 'bottom' }, tooltip: { callbacks: { title: (items) => { const week = weeks[items[0].dataIndex]; return `${week.week_start} – ${week.week_end}` } } } },
        scales: {
          x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true } },
          km: { beginAtZero: true, position: 'left', title: { display: true, text: 'Distance (km)' } },
          tss: { beginAtZero: true, position: 'right', title: { display: true, text: 'Combined TSS' }, grid: { drawOnChartArea: false } },
        },
      },
    })
    return () => chart.destroy()
  }, [weeks])

  return <section className="full-detail-section weekly-training" aria-labelledby="weekly-training-title">
    <span className="eyebrow">TRAINING HISTORY</span>
    <h2 id="weekly-training-title">Weekly distance &amp; TSS</h2>
    <p className="chart-caption">Last 12 weeks · Monday–Sunday · Running and cycling distances, with combined heart-rate TSS. Current week is in progress. Solid bars: running; striped bars: cycling; dashed line: TSS.</p>
    {error ? <><p role="alert" className="error-message">{error}</p><button className="grade-recalculate" type="button" onClick={() => setRetry((value) => value + 1)}>Try again</button></>
      : !weeks ? <p className="dashboard-state" role="status">Loading weekly training…</p> : <>
        <div className="weekly-training-canvas"><canvas ref={canvas} role="img" aria-label="Weekly running and cycling kilometres with combined TSS. Exact values are in the table below." /></div>
        {weeks.every((week) => week.running_km === 0 && week.cycling_km === 0 && week.scored_activity_count === 0 && week.excluded_activity_count === 0) && <p className="chart-caption">No activities recorded in these weeks.</p>}
        <details><summary>View weekly data and excluded activities</summary><div className="weekly-training-table"><table>
          <caption>Weekly totals. Unavailable values appear as —; excluded activities are omitted from TSS.</caption>
          <thead><tr><th scope="col">Week starting</th><th scope="col">Running (km)</th><th scope="col">Cycling (km)</th><th scope="col">Combined TSS</th><th scope="col">Excluded from TSS</th></tr></thead>
          <tbody>{weeks.map((week) => <tr key={week.week_start}><th scope="row">{week.week_start}</th><td>{week.running_km?.toFixed(1) ?? '—'}</td><td>{week.cycling_km?.toFixed(1) ?? '—'}</td><td>{week.tss?.toFixed(1) ?? '—'}</td><td>{week.excluded_activity_count}</td></tr>)}</tbody>
        </table></div></details>
        {weeks.some((week) => week.excluded_activity_count > 0) && <p className="chart-caption">Some weekly TSS totals are incomplete: activities with missing or invalid heart-rate data, or unsupported sports, were excluded. See weekly data for counts.</p>}
      </>}
  </section>
}
