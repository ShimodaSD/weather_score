import { useCallback, useEffect, useMemo, useState } from 'react'
import { fetchActivityGrades, fetchActivityIndex, startActivityGrade, syncGarminActivities, type ActivityGrade, type ActivityIndex } from './api'

const apiBase = import.meta.env.VITE_API_BASE_URL || '/api'
const formatDate = (value: string) => new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value))
const formatPace = (minutes: number) => `${Math.floor(minutes)}:${String(Math.round(minutes % 1 * 60)).padStart(2, '0')} /km`
const formatWind = (headwind: number | null, wind: number) => headwind === null
  ? `${wind.toFixed(0)} km/h wind`
  : Math.abs(headwind) < 0.5 ? 'Crosswind' : `${Math.abs(headwind).toFixed(0)} km/h ${headwind > 0 ? 'headwind' : 'tailwind'}`

export default function ActivityGradesPage({ token, onTokenChange, onSignIn }: { token: string; onTokenChange: (token: string) => void; onSignIn: () => void }) {
  const [activities, setActivities] = useState<ActivityIndex[]>([])
  const [grades, setGrades] = useState<ActivityGrade[]>([])
  const [loading, setLoading] = useState(Boolean(token))
  const [error, setError] = useState('')
  const [startingId, setStartingId] = useState('')
  const [syncing, setSyncing] = useState(false)
  const [syncMessage, setSyncMessage] = useState('')

  const load = useCallback(async (quiet = false) => {
    if (!token) return
    if (!quiet) setLoading(true)
    try {
      const [nextActivities, nextGrades] = await Promise.all([
        fetchActivityIndex(apiBase, token),
        fetchActivityGrades(apiBase, token),
      ])
      setActivities(nextActivities)
      setGrades(nextGrades)
      setError('')
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : 'Activity grades are unavailable.'
      if (message.includes('sign-in expired')) onTokenChange('')
      setError(message)
    } finally { if (!quiet) setLoading(false) }
  }, [token, onTokenChange])

  useEffect(() => { void load() }, [load])
  const processing = grades.some((grade) => grade.status === 'processing')
  useEffect(() => {
    if (!processing) return
    const timer = window.setInterval(() => { void load(true) }, 2_000)
    return () => window.clearInterval(timer)
  }, [processing, load])

  const byActivity = useMemo(() => new Map(grades.map((grade) => [grade.activity_id, grade])), [grades])

  async function start(id: string) {
    if (startingId) return
    setStartingId(id)
    setError('')
    try {
      const grade = await startActivityGrade(apiBase, id, token)
      setGrades((current) => [grade, ...current.filter((item) => item.activity_id !== id)])
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : 'Could not start activity grading.'
      if (message.includes('sign-in expired')) onTokenChange('')
      setError(message)
    } finally { setStartingId('') }
  }

  async function syncGarmin() {
    if (syncing) return
    setSyncing(true)
    setSyncMessage('')
    setError('')
    try {
      const result = await syncGarminActivities(apiBase, token)
      await load(true)
      setSyncMessage(result.new_activities === 1
        ? '1 new Garmin activity imported.'
        : `${result.new_activities} new Garmin activities imported.`)
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : 'Garmin sync failed.'
      if (message.includes('sign-in expired')) onTokenChange('')
      setError(message)
    } finally { setSyncing(false) }
  }

  return <main id="main" className="grades-page">
    <header className="grades-hero"><div><span className="eyebrow">ROUTE WEATHER, EVERY 200 METRES</span><h1>Activity grades<span className="brand-dot">.</span></h1><p>Match every Garmin route section to historical hourly weather from its recorded date, time, and location.</p></div><div className="grades-hero-tools"><div className="grades-count"><strong>{grades.filter((grade) => grade.status === 'complete').length}</strong><span>routes graded</span></div>{token && <button className="garmin-sync" type="button" disabled={syncing} onClick={() => { void syncGarmin() }}>{syncing ? 'Syncing…' : 'Get new data'}</button>}</div></header>
    {token && syncMessage && <p className="garmin-sync-message" role="status">{syncMessage}</p>}
    {!token ? <section className="predictions-state"><h2>Grade your Garmin routes</h2><p>Sign in to choose an activity and process its historical weather.</p><button className="header-auth" type="button" onClick={onSignIn}>Sign in</button></section>
      : loading ? <p className="dashboard-state" role="status">Loading activities and grades…</p>
        : error && activities.length === 0 ? <section className="predictions-state"><h2>Grades unavailable</h2><p role="alert">{error}</p><button className="header-auth" type="button" onClick={() => { void load() }}>Try again</button></section>
          : <><div className="grades-status" role="status" aria-atomic="true">{processing ? 'Historical weather grading is running. This page will update automatically.' : `${activities.length} Garmin activities ready to grade.`}</div>{error && <p className="error-message" role="alert">{error}</p>}<section className="grade-list" aria-label="Garmin activity grades">{activities.map((activity) => {
            const grade = byActivity.get(activity.activity_id)
            const running = activity.activity_type === 'running'
            return <article className="grade-card" key={activity.activity_id}><div className="grade-card-main"><div><span className="grade-type">{activity.activity_type}</span><h2>{activity.name || 'Untitled activity'}</h2><p>{formatDate(activity.started_at)}</p></div>{grade?.status === 'complete' ? <div className="grade-result"><div className="grade-score" aria-label={`Score ${grade.score} out of 100`}><strong>{grade.score?.toFixed(0)}</strong><span>/ 100</span></div><button className="grade-recalculate" type="button" disabled={startingId === activity.activity_id} onClick={() => { void start(activity.activity_id) }}>{startingId === activity.activity_id ? 'Starting…' : 'Recalculate'}</button></div> : <button className="grade-action" type="button" disabled={!running || grade?.status === 'processing' || startingId === activity.activity_id} onClick={() => { void start(activity.activity_id) }}>{!running ? 'Running only' : grade?.status === 'processing' ? 'Processing…' : startingId === activity.activity_id ? 'Starting…' : grade?.status === 'failed' ? 'Try again' : 'Grade route'}</button>}</div>{grade?.status === 'processing' && <p className="grade-message">Historical weather is being collected for each 200 m section.</p>}{grade?.status === 'failed' && <p className="grade-message grade-failed">{grade.error || 'This route could not be graded.'}</p>}{grade?.status === 'complete' && <details className="grade-segments"><summary>{grade.segments.length} segment grades</summary><div className="grade-table-wrap"><table><thead><tr><th>Distance</th><th>Score</th><th>Pace</th><th>Wind effect</th><th>Estimated WBGT</th></tr></thead><tbody>{grade.segments.map((segment) => <tr key={segment.index}><td>{Math.round(segment.start_distance_m)}–{Math.round(segment.end_distance_m)} m</td><td><strong>{segment.score.toFixed(0)}</strong></td><td>{formatPace(segment.pace_minutes_per_km)}</td><td>{formatWind(segment.headwind_kph, segment.wind_kph)}</td><td>{segment.wbgt_c?.toFixed(1) ?? '—'} °C</td></tr>)}</tbody></table></div></details>}</article>
          })}{activities.length === 0 && <div className="predictions-state"><h2>No Garmin activities found</h2><p>Sync GarminDB, then return here to grade a route.</p></div>}</section></>}
  </main>
}
