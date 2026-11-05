import { useCallback, useEffect, useState } from 'react'
import { fetchRunningImpact, syncGarminActivities, type RunningImpact } from './api'
import GarminSyncProgress, { useGarminSyncProgress } from './GarminSyncProgress'
import { formatDate, formatDuration } from './Activities'

const apiBase = import.meta.env.VITE_API_BASE_URL || '/api'

export default function RunningImpactPage({ token, onTokenChange, onSignIn }: { token: string; onTokenChange: (token: string) => void; onSignIn: () => void }) {
  const [coefficients, setCoefficients] = useState<'male' | 'female'>('male')
  const [data, setData] = useState<RunningImpact | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [retry, setRetry] = useState(0)
  const [syncing, setSyncing] = useState(false)
  const [syncMessage, setSyncMessage] = useState('')
  const [syncError, setSyncError] = useState('')
  const refreshImpact = useCallback(() => setRetry((value) => value + 1), [])
  const syncProgress = useGarminSyncProgress(apiBase, token, syncing, refreshImpact)
  const syncActive = syncing || syncProgress.active

  async function syncGarmin() {
    if (syncActive) return
    setSyncing(true); setSyncMessage(''); setSyncError('')
    try {
      const result = await syncGarminActivities(apiBase, token)
      refreshImpact()
      setSyncMessage(`${result.new_activities} new Garmin ${result.new_activities === 1 ? 'activity' : 'activities'} imported.`)
    } catch (reason) {
      if (reason instanceof Error && reason.message.includes('sign-in expired')) onTokenChange('')
      setSyncError(reason instanceof Error ? reason.message : 'Garmin sync failed.')
    } finally { setSyncing(false) }
  }
  useEffect(() => {
    if (!token) { setData(null); return }
    let cancelled = false
    setLoading(true); setError(''); setData(null)
    fetchRunningImpact(apiBase, token, coefficients).then((result) => { if (!cancelled) setData(result) }).catch((reason) => {
      if (cancelled) return
      if (reason instanceof Error && reason.message.includes('sign-in expired')) onTokenChange('')
      setError(reason instanceof Error ? reason.message : 'Could not load training impact.')
    }).finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [token, coefficients, onTokenChange, retry])
  const total = data?.activities.reduce((sum, run) => sum + run.trimp, 0) ?? 0
  return <main id="main" className="predictions-page">
    <header className="predictions-hero"><div><span className="eyebrow">TRAINING, IN CONTEXT</span><h1>Running impact<span className="brand-dot">.</span></h1><p>Review the training load of your recorded runs and see how each estimate is calculated.</p></div>{token && <button className="garmin-sync" type="button" disabled={syncActive} onClick={() => { void syncGarmin() }}>{syncActive ? 'Syncing…' : 'Get new data'}</button>}</header>
    {token && <GarminSyncProgress {...syncProgress} syncing={syncing} />}
    {token && syncMessage && <p className="garmin-sync-message" role="status">{syncMessage}</p>}
    {token && syncError && <p className="error-message" role="alert">{syncError}</p>}
    {!token ? <section className="predictions-state"><h2>Review your runs</h2><p>Sign in to see your training load.</p><button className="header-auth" onClick={onSignIn}>Sign in</button></section> : <>
      <section className="prediction-method impact-coefficients"><div><h2>Study coefficients</h2><p>The study published two sex-specific coefficient sets. Choose the set you want to use; this selection is not saved.</p></div><label>Coefficient set<select value={coefficients} onChange={(event) => setCoefficients(event.target.value as 'male' | 'female')}><option value="male">Male: 0.64 and 1.92</option><option value="female">Female: 0.86 and 1.67</option></select></label></section>
      {loading ? <p className="dashboard-state" role="status">Calculating training load…</p> : error ? <section className="predictions-state"><h2>Training load unavailable</h2><p role="alert">{error}</p><button className="header-auth" onClick={() => setRetry((value) => value + 1)}>Try again</button></section> : data && data.model.model_status !== 'fitted' ? <section className="predictions-state impact-empty"><h2>Personal model unavailable</h2><p>{data.model.run_count === 0 ? 'No eligible runs were found. Sync a run of at least 3 km with a recorded moving time to get started.' : `We found ${data.model.run_count} eligible runs in the latest 180-day window, but could not fit a reliable crossover speed.`}</p><p>The model needs efforts within 3% of at least two different benchmark distances: 5 km, 10 km, half marathon, or marathon. The efforts must also produce a consistent fit. Ordinary training runs may not represent your best effort.</p><a className="impact-link" href="#predictions">See your running predictions <span aria-hidden="true">→</span></a></section> : data && <>
        <div className="prediction-status"><strong>{total.toFixed(0)} TRIMP</strong><span>Combined load across {data.activities.length} eligible runs in the 180 days ending {data.model.season_end_at && formatDate(data.model.season_end_at)}. This is training load, not measured fitness gained.</span></div>
        <section className="prediction-basis"><div><span className="eyebrow">YOUR RUNS</span><h2>Activity contributions</h2></div><div className="prediction-basis-list">{data.activities.map((run) => <div key={run.activity_id}><strong>{run.trimp.toFixed(1)} TRIMP · {run.distance_km.toFixed(2)} km</strong><span>{formatDate(run.started_at)} · {formatDuration(run.moving_seconds)} · relative speed {run.relative_speed.toFixed(2)}</span><a href={`#activity?aid=${encodeURIComponent(run.activity_id)}`}>View run ↗</a></div>)}</div></section>
        <section className="prediction-method"><div><span className="eyebrow">THE CALCULATION</span><h2>Duration × intensity</h2></div><p>TRIMP = moving minutes × κ₁ × relative speed × e^(κ₂ × relative speed). Relative speed is average speed divided by your fitted crossover speed ({data.model.vm_mps?.toFixed(2)} m/s). Your selected coefficients are {coefficients === 'male' ? '0.64 and 1.92' : '0.86 and 1.67'}. The model uses recorded moving time and runs of at least 3 km; unusually high speed ratios are excluded. <a href="#predictions">See the benchmark method</a>.</p></section>
      </>}
      <section className="prediction-method"><div><h2>What this means</h2></div><p>The <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC7538888/" target="_blank" rel="noreferrer">Emig–Peltonen study</a> examined about 14,000 marathon runners. It associated seasonal training impulse with endurance across runners; it did not measure fitness gained from an individual workout. Training pace, terrain, missing activities and the quality of your benchmarks affect this estimate. It does not account for cycling or other sports.</p></section>
    </>}
  </main>
}
