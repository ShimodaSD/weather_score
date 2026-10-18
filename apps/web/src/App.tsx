import { lazy, Suspense, useEffect, useRef, useState, type FormEvent, type CSSProperties } from 'react'
import { SESSION_AUTH, endSession, fetchAccessToken, fetchRunGrade, fetchRunScore, hasSession, type LocationOption, type RunGrade } from './api'
import Activities from './Activities'

const ActivityDetailPage = lazy(() => import('./ActivityDetailPage'))
const RunningPredictionsPage = lazy(() => import('./RunningPredictionsPage'))
const ActivityGradesPage = lazy(() => import('./ActivityGradesPage'))
const ProfilePage = lazy(() => import('./ProfilePage'))
const apiBase = import.meta.env.VITE_API_BASE_URL || '/api'

function Icon({ name, className = '' }: { name: 'wind' | 'arrow' | 'pin' | 'run' | 'sun'; className?: string }) {
  const paths = {
    wind: <><path d="M3 8h12a3 3 0 1 0-3-3M3 12h16a3 3 0 1 1-3 3M3 16h6a3 3 0 1 1-3 3" /></>,
    arrow: <><path d="M4 12h15m-6-6 6 6-6 6" /></>,
    pin: <><path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z" /><circle cx="12" cy="10" r="2" /></>,
    run: <><circle cx="15" cy="4" r="2" /><path d="m5 10 5-3 4 3 5 1m-9-4-2 7 5 3-1 5m-4-8-3 5H2" /></>,
    sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5" /></>,
  }
  return <svg className={className} width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>
}

export default function App() {
  const [address, setAddress] = useState('')
  const [pace, setPace] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [token, setToken] = useState('')
  const [checkingSession, setCheckingSession] = useState(true)
  const [signInError, setSignInError] = useState('')
  const [signOutError, setSignOutError] = useState('')
  const [signingIn, setSigningIn] = useState(false)
  const [result, setResult] = useState<{ score: number; grade?: RunGrade; address: string; pace: string } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [options, setOptions] = useState<LocationOption[]>([])
  const [selectedOption, setSelectedOption] = useState('')
  const busy = useRef(false)
  const signInDialog = useRef<HTMLDialogElement>(null)
  const [route, setRoute] = useState(window.location.hash)
  useEffect(() => {
    const onHashChange = () => setRoute(window.location.hash)
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])
  useEffect(() => {
    let cancelled = false
    hasSession(apiBase).then((active) => {
      if (!cancelled && active) setToken(SESSION_AUTH)
    }).finally(() => { if (!cancelled) setCheckingSession(false) })
    return () => { cancelled = true }
  }, [])
  const activityId = route.startsWith('#activity?') ? new URLSearchParams(route.slice('#activity?'.length)).get('aid') : null
  const isActivities = route === '#activities' || activityId !== null
  const isPredictions = route === '#predictions'
  const isGrades = route === '#grades'
  const isProfile = route === '#profile'

  function openSignIn() {
    setSignInError('')
    signInDialog.current?.showModal()
  }

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSigningIn(true)
    setSignInError('')
    try {
      await fetchAccessToken(apiBase, username, password)
      setToken(SESSION_AUTH)
      setUsername('')
      setPassword('')
      setError('')
      setSignOutError('')
      signInDialog.current?.close()
    } catch (reason) {
      setSignInError(reason instanceof Error ? reason.message : 'Could not sign in.')
    } finally { setSigningIn(false) }
  }

  async function signOut() {
    setSignOutError('')
    try {
      await endSession(apiBase)
      setToken('')
      setResult(null)
    } catch {
      setSignOutError('Could not sign out. Please try again.')
    }
  }

  async function checkConditions(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy.current) return
    const location = address.trim()
    if (!location) { setError('Enter a town, suburb, or address.'); return }
    busy.current = true
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const selected = options[Number(selectedOption)]
      const response = pace.trim()
        ? await fetchRunGrade(apiBase, location, pace, selected)
        : await fetchRunScore(apiBase, location, selected)
      if (!Array.isArray(response)) {
        setResult(typeof response === 'number'
          ? { score: response, address: selected?.name ?? location, pace: '' }
          : { score: response.score, grade: response, address: selected?.name ?? location, pace: pace.trim() })
      } else {
        setOptions(response)
        setSelectedOption('')
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Something went wrong. Please try again.')
    } finally {
      busy.current = false
      setLoading(false)
    }
  }

  if (checkingSession) return <main id="main"><p className="dashboard-state" role="status">Restoring session…</p></main>

  return <>
    <a className="skip-link" href="#main">Skip to content</a>
    <header className="header">
      <a className="brand" href="#check" aria-label="Wind Score home"><span className="brand-mark"><Icon name="wind" /></span>windscore<span className="brand-dot">.</span></a>
      <nav aria-label="Main navigation"><a className={!isActivities && !isPredictions && !isGrades ? 'nav-active' : ''} href="#check" aria-current={!isActivities && !isPredictions && !isGrades ? 'page' : undefined}>Run conditions</a><a className={isActivities ? 'nav-active' : ''} href="#activities" aria-current={isActivities ? 'page' : undefined}>Activities</a><a className={isGrades ? 'nav-active' : ''} href="#grades" aria-current={isGrades ? 'page' : undefined}>Route grades</a><a className={isPredictions ? 'nav-active' : ''} href="#predictions" aria-current={isPredictions ? 'page' : undefined}>Predictions</a></nav>
      {signOutError && <span className="error-message" role="alert">{signOutError}</span>}{token ? <button className="header-auth" type="button" onClick={() => { void signOut() }} disabled={loading}>Sign out</button> : !isActivities && <button className="header-auth" type="button" onClick={openSignIn}>Sign in</button>}
    </header>
    <dialog className="sign-in-dialog" ref={signInDialog} aria-labelledby="sign-in-title">
      <div className="dialog-heading"><div><span className="eyebrow">WIND SCORE</span><h2 id="sign-in-title">Sign in</h2></div><button type="button" className="dialog-close" aria-label="Close sign-in" onClick={() => signInDialog.current?.close()}>×</button></div>
      <p>Use your account to view activities and predictions.</p>
      <form onSubmit={signIn}><label htmlFor="username">Username</label><input className="text-field" id="username" name="username" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required disabled={signingIn} /><label className="field-label" htmlFor="password">Password</label><input className="text-field" id="password" name="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required disabled={signingIn} /><button className="submit" type="submit" disabled={signingIn}>{signingIn ? 'Signing in…' : 'Sign in'}</button>{signInError && <p className="error-message" role="alert">{signInError}</p>}</form>
    </dialog>

    {isProfile ? <Suspense fallback={<main id="main"><p className="dashboard-state" role="status">Opening profile…</p></main>}><ProfilePage key={token} token={token} onTokenChange={setToken} onSignIn={openSignIn} /></Suspense> : isGrades ? <Suspense fallback={<main id="main" className="grades-page"><p className="dashboard-state" role="status">Opening activity grades…</p></main>}><ActivityGradesPage token={token} onTokenChange={setToken} onSignIn={openSignIn} /></Suspense> : isPredictions ? <Suspense fallback={<main id="main" className="predictions-page"><p className="dashboard-state" role="status">Opening predictions…</p></main>}><RunningPredictionsPage token={token} onTokenChange={setToken} onSignIn={openSignIn} /></Suspense> : isActivities ? activityId && token ? <Suspense fallback={<main id="main" className="full-activity-page"><p className="dashboard-state" role="status">Opening activity details…</p></main>}><ActivityDetailPage id={activityId} token={token} onTokenChange={setToken} /></Suspense> : <Activities key={token} token={token} onTokenChange={setToken} /> : <main id="main">
      <section className="intro" aria-labelledby="page-title">
        <div className="intro-copy"><div className="eyebrow"><span className="tiny-line" /> WEATHER, TRANSLATED FOR RUNNERS</div>
        <h1 id="page-title">Is today a <em>good day to run?</em></h1>
        <p>Get a running score for your location and pace. See how wind and heat stress could affect your effort.</p>
        <span className="intro-reassurance">Free to check · No account needed</span></div>
      </section>

      <section className="workspace" id="check" aria-label="Check running conditions">
        <div className="planner">
          <div className="section-label"><span>THE RUN CHECK</span><Icon name="run" /></div>
          <h2>Check your conditions</h2>
          <p className="muted">Enter where you’ll run and your usual pace.</p>
          <form onSubmit={checkConditions}>
            <label htmlFor="address">Your location</label>
            <div className={`location-input ${error ? 'input-error' : ''}`}><Icon name="pin" /><input id="address" name="address" placeholder="Town, suburb, or street address" value={address} onChange={(event) => { setAddress(event.target.value); setOptions([]); setSelectedOption('') }} required maxLength={300} disabled={loading} aria-describedby={error ? 'location-hint search-error' : 'location-hint'} /></div>
            <p id="location-hint" className="field-hint">Add your city or country for a more accurate match.</p>
            {options.length > 0 && <><label className="location-choice-label" htmlFor="location-choice">Which place did you mean?</label><select id="location-choice" value={selectedOption} onChange={(event) => setSelectedOption(event.target.value)} required disabled={loading}><option value="">Select a location</option>{options.map((option, index) => <option key={`${option.latitude},${option.longitude}`} value={index}>{option.name}</option>)}</select></>}
            <label className="field-label" htmlFor="pace">Average pace per kilometre <span>(optional)</span></label>
            <input className="text-field" id="pace" name="pace" type="text" placeholder="Leave blank to score weather only" pattern="[0-9]+:[0-5][0-9]" value={pace} onChange={(event) => setPace(event.target.value)} maxLength={16} disabled={loading} aria-describedby="pace-hint" />
            <p id="pace-hint" className="field-hint">{pace.trim() ? 'Minutes:seconds, such as 5:20. Your pace is included in the score.' : 'Optional. Without pace, your score uses weather and elevation only.'}</p>
            <button className="submit" type="submit" disabled={loading}>{loading ? 'Checking conditions…' : options.length ? 'Use this location' : 'Get my running score'}<Icon name="arrow" /></button>
            {error && <p className="error-message" id="search-error" role="alert">{error}</p>}
            <p className="form-note">Free, with no sign-in. Your location is used to find local conditions.</p>
          </form>
          <div className="planner-bottom"><span className="small-wind"><Icon name="wind" /></span><p>Made for a run, not just a weather report.</p></div>
        </div>

        <div className="score-panel" aria-busy={loading}>
          <div className="score-top"><span className="section-label">YOUR RUNNING SCORE</span><span className="status-pill"><span />{loading ? 'Checking' : result ? 'Current conditions' : 'Awaiting location'}</span></div>
          <div className="score-content" role="status" aria-live="polite" aria-atomic="true">
            <div className={`score-ring ${loading ? 'loading' : ''}`} style={{ '--score': `${result?.score ?? 0}%` } as CSSProperties}><div className="ring-inner"><span className="score-value">{loading ? '···' : result ? Math.round(result.score) : '—'}</span><span className="score-denominator">OUT OF 100</span></div></div>
            <h2>{loading ? 'Reading the conditions…' : result ? 'Here’s your running outlook.' : 'Your score will appear here.'}</h2>
            <p>{loading ? 'A moment to check the weather where you’re headed.' : result ? <>Running conditions for <strong>{result.address}</strong>{result.pace ? ` at ${result.pace}/km` : ''}.<br />Higher scores mean more suitable conditions.</> : <>Enter your place to see a score out of 100. Add your pace to include its effect on wind exposure.</>}</p>
            {result?.grade && <dl className="grade-details"><div><dt>Running speed</dt><dd>{result.grade.running_speed_kph.toFixed(2)} km/h</dd></div><div><dt>Relative air speed</dt><dd>{result.grade.relative_air_speed_kph.toFixed(2)} km/h</dd></div><div><dt>Wind effort change</dt><dd>{result.grade.wind_metabolic_change_percent > 0 ? '+' : ''}{result.grade.wind_metabolic_change_percent.toFixed(2)}%</dd></div><div><dt>Temperature loss</dt><dd>{result.grade.thermal_performance_loss_percent.toFixed(2)}%</dd></div></dl>}
          </div>
          <div className="score-legend"><span>Less suitable</span><div /><span>More suitable</span></div>
          <div className="contours" aria-hidden="true" />
        </div>
      </section>

      <section className="explainer" id="how-it-works" aria-labelledby="explainer-title">
        <div className="explainer-heading"><span className="eyebrow">HOW IT WORKS</span><h2 id="explainer-title">A forecast is only the beginning.</h2><p>Turn conditions into a more useful plan for your next run.</p></div>
        <div className="explanation"><span className="feature-icon"><Icon name="pin" /></span><h3>Local to your next step</h3><p>Start with an address. We find the conditions for the place you want to run.</p></div>
        <div className="explanation"><span className="feature-icon"><Icon name="wind" /></span><h3>Beyond the forecast</h3><p>Wind gusts and heat stress shape your running score at your pace.</p></div>
        <div className="explanation"><span className="feature-icon"><Icon name="run" /></span><h3>You take it from here</h3><p>Use your score to help plan your run. Always check local alerts before heading out.</p></div>
      </section>
      <aside className="outside-note"><span aria-hidden="true">↗</span><p>Ready to see what today feels like at your pace?</p><a href="#check">Check conditions <span aria-hidden="true">→</span></a></aside>
    </main>}
    <footer><a className="brand footer-brand" href="#"><Icon name="wind" />windscore.</a><p>A little clarity. A little fresh air.</p><span>Built for the way you move.</span></footer>
  </>
}
