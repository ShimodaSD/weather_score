import { useEffect, useState, type FormEvent } from 'react'
import { SESSION_AUTH, fetchAccessToken, fetchActivityIndex, fetchActivitySummary, type Activity, type ActivityIndex } from './api'

const apiBase = import.meta.env.VITE_API_BASE_URL || '/api'
export const formatNumber = (value: number | null | undefined, unit = '', digits = 0) => value == null ? '—' : `${value.toFixed(digits)}${unit}`
export const formatDuration = (seconds: number | null | undefined) => {
  if (seconds == null) return '—'
  const rounded = Math.round(seconds)
  const hours = Math.floor(rounded / 3600)
  const minutes = Math.floor((rounded % 3600) / 60)
  return hours ? `${hours}h ${String(minutes).padStart(2, '0')}m` : `${minutes}m ${String(rounded % 60).padStart(2, '0')}s`
}
export const formatPace = (seconds: number | null | undefined) => seconds == null ? '—' : `${Math.floor(Math.round(seconds) / 60)}:${String(Math.round(seconds) % 60).padStart(2, '0')} /km`
export const formatDate = (value: string) => new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(value))

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="activity-metric"><dt>{label}</dt><dd>{value}</dd></div>
}

export default function Activities({ token, onTokenChange }: { token: string; onTokenChange: (token: string) => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [activities, setActivities] = useState<ActivityIndex[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [summary, setSummary] = useState<Activity | null>(null)
  const [section, setSection] = useState<'Overview' | 'Effort' | 'Terrain'>('Overview')
  const [sport, setSport] = useState('All activities')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [indexRetry, setIndexRetry] = useState(0)
  const [summaryRetry, setSummaryRetry] = useState(0)
  const [error, setError] = useState('')
  const [summaryError, setSummaryError] = useState('')

  useEffect(() => {
    if (!token) return
    let cancelled = false
    setLoading(true)
    setError('')
    fetchActivityIndex(apiBase, token).then((items) => {
      if (cancelled) return
      setActivities(items)
      setSelectedId(items[0]?.activity_id ?? null)
    }).catch((reason) => {
      if (cancelled) return
      if (reason instanceof Error && reason.message.includes('sign-in expired')) onTokenChange('')
      setError(reason instanceof Error ? reason.message : 'Could not load activities.')
    }).finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [token, onTokenChange, indexRetry])

  const sports = [...new Set(activities.map((activity) => activity.activity_type))].sort()
  const shown = activities.filter((activity) => (sport === 'All activities' || activity.activity_type === sport)
    && `${activity.name ?? ''} ${activity.activity_type} ${activity.activity_id}`.toLowerCase().includes(search.toLowerCase()))
  const selected = shown.find((activity) => activity.activity_id === selectedId) ?? shown[0]
  const selectedIndex = shown.findIndex((activity) => activity.activity_id === selected?.activity_id)

  useEffect(() => {
    if (!token || !selected?.activity_id) return
    let cancelled = false
    setSummary(null)
    setSummaryError('')
    setSummaryLoading(true)
    fetchActivitySummary(apiBase, selected.activity_id, token).then((item) => {
      if (!cancelled) setSummary(item)
    }).catch((reason) => {
      if (cancelled) return
      if (reason instanceof Error && reason.message.includes('sign-in expired')) onTokenChange('')
      setSummaryError(reason instanceof Error ? reason.message : 'Could not load this activity.')
    }).finally(() => { if (!cancelled) setSummaryLoading(false) })
    return () => { cancelled = true }
  }, [selected?.activity_id, token, onTokenChange, summaryRetry])

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      await fetchAccessToken(apiBase, username, password)
      onTokenChange(SESSION_AUTH)
      setUsername('')
      setPassword('')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not sign in.')
    } finally { setLoading(false) }
  }

  function selectActivity(id: string) {
    setSelectedId(id)
    setSection('Overview')
  }

  const detail = summary?.activity_id === selected?.activity_id ? summary : null

  return <main id="main" className="activity-dashboard">
    <div className="dashboard-heading"><div><span className="eyebrow">YOUR MOVEMENT, AT A GLANCE</span><h1>Activity dashboard<span className="brand-dot">.</span></h1><p>Explore your recorded activities and the numbers behind each one.</p></div></div>
    {!token ? <section className="dashboard-login" aria-labelledby="activities-signin"><div><span className="eyebrow">WELCOME BACK</span><h2 id="activities-signin">See your activities</h2><p>Sign in to view the activities saved to your account.</p></div><form onSubmit={signIn}><label htmlFor="activity-username">Username</label><input id="activity-username" className="text-field" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required disabled={loading} /><label htmlFor="activity-password">Password</label><input id="activity-password" className="text-field" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required disabled={loading} /><button className="submit" disabled={loading}>{loading ? 'Signing in…' : 'Sign in and view activities'}</button>{error && <p className="error-message" role="alert">{error}</p>}</form></section> : <>
      <section className="dashboard-stats" aria-label="Activity totals"><div><span>ALL ACTIVITIES</span><strong>{activities.length}</strong><small>Recorded sessions</small></div><div><span>ACTIVITY TYPES</span><strong>{sports.length}</strong><small>Ways you moved</small></div><div><span>MOST RECENT</span><strong className="dashboard-date">{activities[0] ? formatDate(activities[0].started_at) : '—'}</strong><small>Latest recorded activity</small></div></section>
      <div className="dashboard-grid">
        <section className="activity-list" aria-labelledby="activity-list-title">
          <div className="activity-list-head"><div><span className="eyebrow">YOUR LIBRARY</span><h2 id="activity-list-title">All activities</h2></div><span className="list-count">{shown.length} shown</span></div>
          <div className="activity-filters"><label htmlFor="activity-search">Search activities<input id="activity-search" type="search" placeholder="Name, sport, or ID" value={search} onChange={(event) => setSearch(event.target.value)} /></label><label htmlFor="activity-sport">Activity type<select id="activity-sport" value={sport} onChange={(event) => setSport(event.target.value)}><option>All activities</option>{sports.map((type) => <option key={type} value={type}>{type}</option>)}</select></label></div>
          {loading ? <p className="dashboard-state" role="status">Loading your activities…</p> : shown.length === 0 ? <p className="dashboard-state">{activities.length ? 'No activities match this search.' : 'No activities available yet.'}</p> : <div className="activity-rows">{shown.map((activity) => <button key={activity.activity_id} className={`activity-row ${selected?.activity_id === activity.activity_id ? 'is-active' : ''}`} onClick={() => selectActivity(activity.activity_id)} aria-pressed={selected?.activity_id === activity.activity_id}><span className="activity-row-icon" aria-hidden="true">{activity.activity_type.slice(0, 1).toUpperCase()}</span><span className="activity-row-main"><strong>{activity.name || activity.activity_type}</strong><small>{formatDate(activity.started_at)} · {activity.activity_type}</small></span><span className="activity-row-chevron" aria-hidden="true">›</span></button>)}</div>}
          {error && <div className="dashboard-retry"><p className="error-message" role="alert">{error}</p><button type="button" onClick={() => setIndexRetry((count) => count + 1)}>Try again</button></div>}
        </section>
        <section className="activity-detail" aria-labelledby="activity-detail-title">
          {selected ? <>
            <div className="detail-top"><span className="eyebrow">ACTIVITY DETAILS</span><span className="detail-type">{selected.activity_type}</span></div>
            <h2 id="activity-detail-title">{selected.name || selected.activity_type}</h2><p className="detail-date">{formatDate(selected.started_at)} · ID {selected.activity_id}</p>
            {summaryError ? <div className="dashboard-retry"><p className="error-message" role="alert">{summaryError}</p><button type="button" onClick={() => setSummaryRetry((count) => count + 1)}>Try again</button></div> : summaryLoading || !detail ? <p className="dashboard-state" role="status">Loading activity summary…</p> : <>
              <div className="detail-feature"><div><span>DISTANCE</span><strong>{formatNumber(detail.distance_km, '', 2)} <small>km</small></strong></div><div><span>MOVING TIME</span><strong>{formatDuration(detail.moving_seconds ?? detail.elapsed_seconds)}</strong></div></div>
              <nav className="detail-tabs" aria-label="Activity information">{(['Overview', 'Effort', 'Terrain'] as const).map((tab) => <button key={tab} type="button" aria-pressed={section === tab} className={section === tab ? 'active' : ''} onClick={() => setSection(tab)}>{tab}</button>)}</nav>
              <dl className="detail-metrics" aria-live="polite">{section === 'Overview' ? <><Metric label="Elapsed time" value={formatDuration(detail.elapsed_seconds)} /><Metric label="Moving time" value={formatDuration(detail.moving_seconds)} /><Metric label="Average speed" value={formatNumber(detail.average_speed_kph, ' km/h', 1)} /><Metric label="Average pace" value={formatPace(detail.average_pace_seconds_per_km)} /></> : section === 'Effort' ? <><Metric label="Average heart rate" value={formatNumber(detail.average_heart_rate_bpm, ' bpm')} /><Metric label="Maximum heart rate" value={formatNumber(detail.maximum_heart_rate_bpm, ' bpm')} /><Metric label="Calories" value={formatNumber(detail.calories, ' kcal')} /><Metric label="Average cadence" value={formatNumber(detail.average_cadence_per_minute, ' /min')} /><Metric label="Training effect" value={formatNumber(detail.training_effect, '', 1)} /><Metric label="Anaerobic effect" value={formatNumber(detail.anaerobic_training_effect, '', 1)} /></> : <><Metric label="Elevation gain" value={formatNumber(detail.elevation_gain_m, ' m')} /><Metric label="Elevation loss" value={formatNumber(detail.elevation_loss_m, ' m')} /><Metric label="Average temperature" value={formatNumber(detail.average_temperature_c, ' °C', 1)} /></>}</dl>
              <a className="full-detail-link" href={`#activity?aid=${encodeURIComponent(detail.activity_id)}`}>View full activity details <span aria-hidden="true">→</span></a>
            </>}
            <div className="detail-navigation"><button disabled={selectedIndex <= 0} onClick={() => selectActivity(shown[selectedIndex - 1].activity_id)}>← Newer</button><span>{selectedIndex + 1} of {shown.length}</span><button disabled={selectedIndex >= shown.length - 1} onClick={() => selectActivity(shown[selectedIndex + 1].activity_id)}>Older →</button></div>
          </> : <div className="detail-empty"><h2 id="activity-detail-title">Choose an activity</h2><p>Select one from the list to see its main information.</p></div>}
        </section>
      </div>
    </>}
  </main>
}
