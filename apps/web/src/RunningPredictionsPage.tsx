import { useEffect, useState } from 'react'
import { fetchRunningPredictions, type RunningPredictions } from './api'
import { formatDate, formatPace } from './Activities'

const apiBase = import.meta.env.VITE_API_BASE_URL || '/api'

function formatRaceTime(seconds: number): string {
  const rounded = Math.round(seconds)
  const hours = Math.floor(rounded / 3600)
  const minutes = Math.floor((rounded % 3600) / 60)
  const rest = String(rounded % 60).padStart(2, '0')
  return hours ? `${hours}:${String(minutes).padStart(2, '0')}:${rest}` : `${minutes}:${rest}`
}

export default function RunningPredictionsPage({ token, onTokenChange, onSignIn }: { token: string; onTokenChange: (token: string) => void; onSignIn: () => void }) {
  const [data, setData] = useState<RunningPredictions | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    if (!token) { setData(null); return }
    let cancelled = false
    setData(null)
    setLoading(true)
    setError('')
    fetchRunningPredictions(apiBase, token).then((result) => {
      if (!cancelled) setData(result)
    }).catch((reason) => {
      if (cancelled) return
      if (reason instanceof Error && reason.message.includes('sign-in expired')) onTokenChange('')
      setError(reason instanceof Error ? reason.message : 'Could not load running predictions.')
    }).finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [token, onTokenChange, retry])

  return <main id="main" className="predictions-page">
    <header className="predictions-hero"><div><span className="eyebrow">YOUR RUNNING, PROJECTED</span><h1>What could you run<span className="brand-dot">?</span></h1><p>Study-based outlooks for 5, 10, 21, and 42 kilometres from your recorded running efforts.</p></div>{data?.run_count ? <div className="predictions-count"><strong>{data.run_count}</strong><span>recent runs analysed</span></div> : null}</header>
    {!token ? <section className="predictions-state"><h2>See your predicted times</h2><p>Sign in to calculate estimates from your running activities.</p><button className="header-auth" type="button" onClick={onSignIn}>Sign in</button></section>
      : loading ? <p className="dashboard-state" role="status">Calculating your running predictions…</p>
        : error ? <section className="predictions-state"><h2>Predictions unavailable</h2><p role="alert">{error}</p><button className="header-auth" type="button" onClick={() => setRetry((count) => count + 1)}>Try again</button></section>
          : data?.predictions.length ? <>
            <div className={`prediction-status ${data.model_status === 'range' ? 'prediction-status-caution' : ''}`} role="status"><strong>{data.model_status === 'fitted' ? 'Personal model fitted' : 'Estimated range'}</strong><span>{data.model_status === 'fitted' ? `Your aerobic power and endurance were fitted from ${data.basis.length} benchmark efforts.` : 'Your recent runs do not establish a reliable personal endurance value. The ranges use the study’s published parameter bounds.'}</span></div>
            <section className="prediction-grid" aria-label="Predicted running times">{data.predictions.map((item) => {
              const beyondLongest = data.longest_run_km !== null && item.distance_km > data.longest_run_km
              const ranged = item.predicted_seconds === null
              return <article className="prediction-card" key={item.distance_km}>
                <div className="prediction-card-top"><span>{item.distance_km} KM</span>{beyondLongest && <span className="prediction-caution">Beyond longest run</span>}</div>
                <strong className={`prediction-time ${ranged ? 'prediction-time-range' : ''}`}>{ranged ? `${formatRaceTime(item.low_seconds)}–${formatRaceTime(item.high_seconds)}` : formatRaceTime(item.predicted_seconds!)}</strong>
                <span className="prediction-pace">{ranged ? `${formatPace(item.low_seconds / item.distance_km)}–${formatPace(item.high_seconds / item.distance_km)}` : formatPace(item.predicted_seconds! / item.distance_km)} projected pace</span>
                <div className="prediction-source"><span>{ranged ? item.low_seconds === item.high_seconds ? 'Recorded benchmark' : 'Study-bounded outlook' : 'Personal endurance model'}</span><span>{beyondLongest ? 'Longer than recorded runs' : 'Within recorded distance'}</span></div>
              </article>
            })}</section>
            <section className="prediction-basis" aria-labelledby="prediction-basis-title"><div><span className="eyebrow">RECORDED BENCHMARKS</span><h2 id="prediction-basis-title">What the model used</h2></div><div className="prediction-basis-list">{data.basis.map((item) => <div key={item.distance_km}><strong>{item.distance_km} km · {formatRaceTime(item.moving_seconds)}</strong><span>{item.source_distance_km.toFixed(1)} km run on {formatDate(item.source_started_at)}</span><a href={`#activity?aid=${encodeURIComponent(item.source_activity_id)}`}>View run ↗</a></div>)}</div></section>
            <section className="prediction-method" aria-labelledby="prediction-method-title"><div><span className="eyebrow">HOW THESE OUTLOOKS WORK</span><h2 id="prediction-method-title">A guide, not a guarantee.</h2></div><p>Based on the <a href="https://www.nature.com/articles/s41467-020-18737-6" target="_blank" rel="noreferrer">Emig–Peltonen running study</a>: we use the fastest recorded efforts near 5 km, 10 km, half-marathon, and marathon distances from the latest 180-day running window. A personal estimate needs at least two consistent benchmarks. Otherwise, the study’s parameter bounds produce a range anchored to the longest available benchmark. {data.season_end_at ? `Window ends ${formatDate(data.season_end_at)}.` : ''} Training runs may not represent race effort, and weather, terrain, and preparation can change actual results.</p></section>
          </> : <section className="predictions-state"><h2>No usable benchmark yet</h2><p>Record a run close to 5 km, 10 km, 21.1 km, or 42.2 km with distance and moving time to see a study-based outlook.</p><a className="header-auth" href="#activities">View activities</a></section>}
  </main>
}
