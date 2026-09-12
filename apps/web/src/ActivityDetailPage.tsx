import { useEffect, useMemo, useRef, useState } from 'react'
import { Chart, Legend, LineController, LineElement, LinearScale, PointElement, Tooltip, type Plugin } from 'chart.js'
import { fetchActivityDetail, type ActivityDetail } from './api'
import { formatDate, formatDuration, formatNumber, formatPace } from './Activities'
import { buildActivitySeries, buildLapMarkers, MAX_PACE_MIN_PER_KM, MIN_PACE_MIN_PER_KM, PACE_ZONES, paceZoneName } from './activityChart'

const apiBase = import.meta.env.VITE_API_BASE_URL || '/api'
Chart.register(LineController, LineElement, PointElement, LinearScale, Legend, Tooltip)
const paceZoneBands: Plugin<'line'> = {
  id: 'paceZoneBands',
  beforeDatasetsDraw(chart) {
    const scale = chart.scales.pace
    if (!scale) return
    const { ctx, chartArea: { left, right, top, bottom } } = chart
    ctx.save()
    ctx.globalAlpha = 0.6
    for (const zone of PACE_ZONES) {
      const fast = scale.getPixelForValue(zone.fastSeconds / 60)
      const slow = scale.getPixelForValue(zone.slowSeconds / 60)
      const start = zone.name === 'Zona 6' ? top : Math.max(top, Math.min(fast, slow))
      const end = Math.min(bottom, Math.max(fast, slow))
      if (end > start) {
        ctx.fillStyle = zone.color
        ctx.fillRect(left, start, right - left, end - start)
      }
    }
    ctx.restore()
  },
}

function Stat({ label, value }: { label: string; value: string }) {
  return <div className="activity-metric"><dt>{label}</dt><dd>{value}</dd></div>
}

function HeartRateChart({ records, laps, startedAt, elapsedSeconds }: { records: Record<string, unknown>[]; laps: Record<string, unknown>[]; startedAt: string; elapsedSeconds: number }) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const series = useMemo(() => buildActivitySeries(records, startedAt), [records, startedAt])
  const lapMarkers = useMemo(() => buildLapMarkers(laps, startedAt, elapsedSeconds), [laps, startedAt, elapsedSeconds])
  const hasData = series.heartRate.some((point) => point.y !== null) || series.pace.some((point) => point.y !== null)
  const hasAdjustedPace = series.adjustedPace.some((point) => point.y !== null)

  useEffect(() => {
    if (!canvas.current || !hasData) return
    const style = getComputedStyle(canvas.current)
    const heartRateColor = style.getPropertyValue('--chart-heart-rate').trim()
    const paceColor = style.getPropertyValue('--chart-pace').trim()
    const adjustedColor = style.getPropertyValue('--chart-adjusted-pace').trim()
    const lapColor = style.getPropertyValue('--chart-lap').trim()
    const lapBars: Plugin<'line'> = {
      id: 'lapBars',
      afterDatasetsDraw(chart) {
        const scale = chart.scales.x
        if (!scale) return
        const { ctx, chartArea: { left, right, top, bottom } } = chart
        ctx.save()
        ctx.strokeStyle = lapColor
        ctx.fillStyle = lapColor
        ctx.lineWidth = 1.5
        ctx.font = '600 10px system-ui'
        ctx.textAlign = 'center'
        let lastLabel = -Infinity
        for (const marker of lapMarkers) {
          const x = scale.getPixelForValue(marker.x)
          if (x < left || x > right) continue
          ctx.beginPath()
          ctx.moveTo(x, top)
          ctx.lineTo(x, bottom)
          ctx.stroke()
          if (x - lastLabel >= 20) {
            ctx.fillText(marker.label, x, top + 11)
            lastLabel = x
          }
        }
        ctx.restore()
      },
    }
    const chart = new Chart(canvas.current, {
      type: 'line',
      plugins: [paceZoneBands, lapBars],
      data: { datasets: [
        { label: 'Heart rate (bpm)', data: series.heartRate.map((point) => ({ x: point.x, y: point.y ?? NaN })), yAxisID: 'bpm', borderColor: heartRateColor, backgroundColor: heartRateColor, borderWidth: 2, pointRadius: 0, spanGaps: false },
        { label: 'Pace (min/km)', data: series.pace.map((point) => ({ x: point.x, y: point.y ?? NaN })), yAxisID: 'pace', borderColor: paceColor, backgroundColor: paceColor, borderWidth: 2, pointRadius: 0, spanGaps: false },
        ...(hasAdjustedPace ? [{ label: 'Climb-adjusted speed (pace equivalent)', data: series.adjustedPace.map((point) => ({ x: point.x, y: point.y ?? NaN })), yAxisID: 'pace', borderColor: adjustedColor, backgroundColor: adjustedColor, borderWidth: 2, borderDash: [6, 4], pointRadius: 0, spanGaps: false }] : []),
      ] },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        parsing: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 18 } },
          tooltip: { callbacks: {
            title: (items) => `${Number(items[0]?.parsed.x ?? 0).toFixed(1)} ${series.xUnit === 'minutes' ? 'elapsed min' : 'samples'}`,
            afterTitle: (items) => `Zone: ${paceZoneName(series.pace[items[0]?.dataIndex ?? -1]?.y ?? MAX_PACE_MIN_PER_KM)}`,
            label: (item) => item.parsed.y == null ? '' : item.datasetIndex === 0 ? `Heart rate: ${Math.round(item.parsed.y)} bpm` : item.datasetIndex === 2 ? `Climb-adjusted speed: ${(60 / item.parsed.y).toFixed(1)} km/h (${formatPace(item.parsed.y * 60)})` : item.parsed.y >= MAX_PACE_MIN_PER_KM ? 'Pace: 9:00/km or slower, or no speed' : `Pace: ${formatPace(item.parsed.y * 60)}`,
          } },
        },
        scales: {
          x: { type: 'linear', min: 0, ...(series.xUnit === 'minutes' && elapsedSeconds > 0 ? { max: elapsedSeconds / 60 } : {}), title: { display: true, text: series.xUnit === 'minutes' ? 'Elapsed minutes' : 'Recorded sample' } },
          bpm: { type: 'linear', position: 'left', title: { display: true, text: 'Heart rate (bpm)' } },
          pace: { type: 'linear', position: 'right', reverse: true, suggestedMin: MIN_PACE_MIN_PER_KM, max: MAX_PACE_MIN_PER_KM, title: { display: true, text: 'Pace (min/km)' }, grid: { drawOnChartArea: false }, ticks: { stepSize: 0.5, callback: (value) => formatPace(Number(value) * 60).replace(' /km', '') } },
        },
      },
    })
    return () => chart.destroy()
  }, [series, hasData, hasAdjustedPace, lapMarkers, elapsedSeconds])

  return <section className="full-detail-section" aria-labelledby="heart-rate-title"><div className="full-detail-section-head"><h2 id="heart-rate-title">Heart rate & pace zones</h2><span>{records.length.toLocaleString()} recorded samples</span></div>{hasData ? <div className="activity-combined-chart"><canvas ref={canvas} role="img" aria-label={`Heart rate and pace over shaded pace zones with ${lapMarkers.length} lap-end markers; climb-adjusted speed appears when elevation data is available; Zona 6 includes all paces faster than 4:10 per kilometre`}>Heart rate and pace chart</canvas></div> : <p className="full-detail-empty">No recorded samples are available for this chart.</p>}<div className="pace-zone-legend" aria-label="Pace zone bands">{PACE_ZONES.map((zone) => <span key={zone.name}><i style={{ backgroundColor: zone.color }} aria-hidden="true" /><strong>{zone.name}</strong> {zone.name === 'Zona 6' ? '<4:10' : `${formatPace(zone.fastSeconds).replace(' /km', '')}–${formatPace(zone.slowSeconds).replace(' /km', '')}`}</span>)}</div><p className="chart-caption">{hasAdjustedPace ? 'The dashed line estimates flat-equivalent speed from uphill gain over a rolling 100 m; hover for km/h.' : 'Climb-adjusted speed is unavailable without enough altitude and distance data.'} {lapMarkers.length ? 'Vertical bars mark lap ends; numbers appear where space allows.' : ''} Missing or slower speed is shown at 9:00/km.</p></section>
}

function RawEntries({ title, rows }: { title: string; rows: Record<string, unknown>[] }) {
  return <section className="full-detail-section" id={title.toLowerCase()} aria-labelledby={`${title.toLowerCase()}-title`}>
    <div className="full-detail-section-head"><h2 id={`${title.toLowerCase()}-title`}>{title}</h2><span>{rows.length} recorded</span></div>
    {rows.length ? <div className="raw-entry-list">{rows.map((row, index) => <details key={index} className="raw-entry"><summary>{title === 'Laps' ? 'Lap' : 'Split'} {index + 1}<span>View recorded values</span></summary><dl>{Object.entries(row).filter(([key, value]) => value != null && !key.endsWith('_id') && ['string', 'number', 'boolean'].includes(typeof value)).map(([key, value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{String(value)}</dd></div>)}</dl></details>)}</div> : <p className="full-detail-empty">No {title.toLowerCase()} were recorded for this activity.</p>}
  </section>
}

export default function ActivityDetailPage({ id, token, onTokenChange }: { id: string; token: string; onTokenChange: (token: string) => void }) {
  const [detail, setDetail] = useState<ActivityDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    let cancelled = false
    setDetail(null)
    setLoading(true)
    setError('')
    fetchActivityDetail(apiBase, id, token).then((activity) => {
      if (!cancelled) setDetail(activity)
    }).catch((reason) => {
      if (cancelled) return
      if (reason instanceof Error && reason.message.includes('sign-in expired')) onTokenChange('')
      setError(reason instanceof Error ? reason.message : 'Could not load this activity.')
    }).finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [id, token, onTokenChange, retry])

  return <main id="main" className="full-activity-page">
    <a className="back-to-dashboard" href="#activities">← Back to activity dashboard</a>
    {loading ? <p className="dashboard-state" role="status">Loading activity details…</p> : error ? <div className="full-detail-error"><h1>Activity unavailable</h1><p role="alert">{error}</p><button type="button" onClick={() => setRetry((count) => count + 1)}>Try again</button></div> : detail && <>
      <header className="full-detail-hero"><div><span className="eyebrow">{detail.activity_type.toUpperCase()} · {formatDate(detail.started_at)}</span><h1>{detail.name || detail.activity_type}</h1><p>Activity ID {detail.activity_id} · {new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(new Date(detail.started_at))}</p></div><span className="full-detail-records">{detail.records.length.toLocaleString()} data points</span></header>
      <nav className="full-detail-nav" aria-label="Activity detail sections">{(['Overview', 'Performance', 'Laps', 'Splits', 'Equipment'] as const).map((section) => <button key={section} type="button" onClick={() => document.getElementById(section.toLowerCase())?.scrollIntoView()}>{section}</button>)}</nav>
      <section className="full-detail-highlights" id="overview" aria-label="Activity overview"><div><span>DISTANCE</span><strong>{formatNumber(detail.distance_km, '', 2)} <small>km</small></strong></div><div><span>MOVING TIME</span><strong>{formatDuration(detail.moving_seconds ?? detail.elapsed_seconds)}</strong></div><div><span>AVERAGE PACE</span><strong>{formatPace(detail.average_pace_seconds_per_km)}</strong></div><div><span>AVERAGE SPEED</span><strong>{formatNumber(detail.average_speed_kph, ' km/h', 1)}</strong></div></section>
      <section className="full-detail-section" id="performance" aria-labelledby="performance-title"><div className="full-detail-section-head"><h2 id="performance-title">Performance & conditions</h2></div><dl className="full-detail-metrics"><Stat label="Elapsed time" value={formatDuration(detail.elapsed_seconds)} /><Stat label="Average heart rate" value={formatNumber(detail.average_heart_rate_bpm, ' bpm')} /><Stat label="Maximum heart rate" value={formatNumber(detail.maximum_heart_rate_bpm, ' bpm')} /><Stat label="Calories" value={formatNumber(detail.calories, ' kcal')} /><Stat label="Average cadence" value={formatNumber(detail.average_cadence_per_minute, ' /min')} /><Stat label="Training effect" value={formatNumber(detail.training_effect, '', 1)} /><Stat label="Anaerobic effect" value={formatNumber(detail.anaerobic_training_effect, '', 1)} /><Stat label="Elevation gain" value={formatNumber(detail.elevation_gain_m, ' m')} /><Stat label="Elevation loss" value={formatNumber(detail.elevation_loss_m, ' m')} /><Stat label="Average temperature" value={formatNumber(detail.average_temperature_c, ' °C', 1)} /></dl></section>
      <HeartRateChart records={detail.records} laps={detail.laps} startedAt={detail.started_at} elapsedSeconds={detail.elapsed_seconds} />
      <div className="full-detail-breakdown"><RawEntries title="Laps" rows={detail.laps} /><RawEntries title="Splits" rows={detail.splits} /></div>
      <section className="full-detail-section" id="equipment" aria-labelledby="equipment-title"><div className="full-detail-section-head"><h2 id="equipment-title">Equipment & recording</h2></div><dl className="full-detail-metrics"><Stat label="Recorded data points" value={detail.records.length.toLocaleString()} /><Stat label="Devices" value={detail.devices.length ? detail.devices.map((device) => String(device.product_name ?? device.product ?? device.manufacturer ?? 'Recorded device')).join(', ') : '—'} /></dl></section>
      <p className="raw-data-note">Lap and split values are shown as recorded by GarminDB; their raw fields may use provider-specific units.</p>
    </>}
  </main>
}
