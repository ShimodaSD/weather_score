import { lazy, Suspense, useEffect, useRef, useState, type FormEvent, type CSSProperties } from 'react'
import { SESSION_AUTH, endSession, fetchAccessToken, fetchRunGrade, hasSession, type LocationOption, type RunGrade } from './api'
import Activities from './Activities'

const ActivityDetailPage = lazy(() => import('./ActivityDetailPage'))
const RunningPredictionsPage = lazy(() => import('./RunningPredictionsPage'))
const ActivityGradesPage = lazy(() => import('./ActivityGradesPage'))
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
  const [result, setResult] = useState<{ grade: RunGrade; address: string; pace: string } | null>(null)
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
    if (!pace.trim()) { setError('Enter your average pace per kilometre.'); return }
    if (!token) { setError('Sign in to check your conditions.'); openSignIn(); return }
    busy.current = true
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const selected = options[Number(selectedOption)]
      const response = await fetchRunGrade(apiBase, location, pace, token, selected)
      if (!Array.isArray(response)) {
        setResult({ grade: response, address: selected?.name ?? location, pace: pace.trim() })
        setOptions([])
      } else {
        setOptions(response)
        setSelectedOption('')
      }
    } catch (reason) {
      if (reason instanceof Error && reason.message.includes('sign-in expired')) setToken('')
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
      <nav aria-label="Main navigation"><a className={!isActivities && !isPredictions && !isGrades ? 'nav-active' : ''} href="#check" aria-current={!isActivities && !isPredictions && !isGrades ? 'page' : undefined}>Conditions</a><a className={isActivities ? 'nav-active' : ''} href="#activities" aria-current={isActivities ? 'page' : undefined}>Activities</a><a className={isGrades ? 'nav-active' : ''} href="#grades" aria-current={isGrades ? 'page' : undefined}>Grades</a><a className={isPredictions ? 'nav-active' : ''} href="#predictions" aria-current={isPredictions ? 'page' : undefined}>Predictions</a><a href="#how-it-works">How it works <span aria-hidden="true">↗</span></a></nav>
      {signOutError && <span className="error-message" role="alert">{signOutError}</span>}{token ? <button className="header-auth" type="button" onClick={() => { void signOut() }} disabled={loading}>Sign out</button> : !isActivities && <button className="header-auth" type="button" onClick={openSignIn}>Sign in</button>}
    </header>
    <dialog className="sign-in-dialog" ref={signInDialog} aria-labelledby="sign-in-title">
      <div className="dialog-heading"><div><span className="eyebrow">WIND SCORE</span><h2 id="sign-in-title">Sign in</h2></div><button type="button" className="dialog-close" aria-label="Close sign-in" onClick={() => signInDialog.current?.close()}>×</button></div>
      <p>Use your account to check conditions and view activities.</p>
      <form onSubmit={signIn}><label htmlFor="username">Username</label><input className="text-field" id="username" name="username" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required disabled={signingIn} /><label className="field-label" htmlFor="password">Password</label><input className="text-field" id="password" name="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required disabled={signingIn} /><button className="submit" type="submit" disabled={signingIn}>{signingIn ? 'Signing in…' : 'Sign in'}</button>{signInError && <p className="error-message" role="alert">{signInError}</p>}</form>
    </dialog>

    {isGrades ? <Suspense fallback={<main id="main" className="grades-page"><p className="dashboard-state" role="status">Opening activity grades…</p></main>}><ActivityGradesPage token={token} onTokenChange={setToken} onSignIn={openSignIn} /></Suspense> : isPredictions ? <Suspense fallback={<main id="main" className="predictions-page"><p className="dashboard-state" role="status">Opening predictions…</p></main>}><RunningPredictionsPage token={token} onTokenChange={setToken} onSignIn={openSignIn} /></Suspense> : isActivities ? activityId && token ? <Suspense fallback={<main id="main" className="full-activity-page"><p className="dashboard-state" role="status">Opening activity details…</p></main>}><ActivityDetailPage id={activityId} token={token} onTokenChange={setToken} /></Suspense> : <Activities key={token} token={token} onTokenChange={setToken} /> : <main id="main">
      <section className="intro" aria-labelledby="page-title">
        <div className="eyebrow"><span className="tiny-line" /> A LITTLE WEATHER WISDOM. A BETTER DAY OUT.</div>
        <h1 id="page-title">Find your <em>outside.</em></h1>
        <p>Less checking the forecast. More feeling the fresh air.<br className="desktop-break" /> Know how the weather shapes your next run.</p>
      </section>

      <section className="workspace" id="check" aria-label="Check running conditions">
        <div className="planner">
          <div className="section-label"><span>01 / YOUR NEXT ADVENTURE</span><Icon name="sun" /></div>
          <h2>Where are you heading?</h2>
          <p className="muted">A good day outside starts right here.</p>
          <form onSubmit={checkConditions}>
            <label htmlFor="address">Your location</label>
            <div className={`location-input ${error ? 'input-error' : ''}`}><Icon name="pin" /><input id="address" name="address" placeholder="Town, suburb, or street address" value={address} onChange={(event) => { setAddress(event.target.value); setOptions([]); setSelectedOption('') }} required maxLength={300} disabled={loading} aria-describedby={error ? 'location-hint search-error' : 'location-hint'} /></div>
            <p id="location-hint" className="field-hint">Add your city or country for a more accurate match.</p>
            <label className="field-label" htmlFor="pace">Average pace per kilometre</label>
            <input className="text-field" id="pace" name="pace" type="text" placeholder="5:20" pattern="[0-9]+:[0-5][0-9]" value={pace} onChange={(event) => setPace(event.target.value)} required maxLength={16} disabled={loading} aria-describedby="pace-hint" />
            <p id="pace-hint" className="field-hint">Minutes:seconds, such as 5:20 for five minutes and twenty seconds.</p>
            {options.length > 0 && <><label className="location-choice-label" htmlFor="location-choice">Which place did you mean?</label><select id="location-choice" value={selectedOption} onChange={(event) => setSelectedOption(event.target.value)} required disabled={loading}><option value="">Select a location</option>{options.map((option, index) => <option key={`${option.latitude},${option.longitude}`} value={index}>{option.name}</option>)}</select></>}
            <button className="submit" type="submit" disabled={loading}>{loading ? 'Checking conditions…' : options.length ? 'Use this location' : 'Check my conditions'}<Icon name="arrow" /></button>
            {error && <p className="error-message" id="search-error" role="alert">{error}</p>}
            <p className="form-note">Your location is only used to find your conditions.</p>
          </form>
          <div className="planner-bottom"><span className="small-wind"><Icon name="wind" /></span><p>A little headwind shouldn’t be a guessing game.</p></div>
        </div>

        <div className="score-panel" aria-busy={loading}>
          <div className="score-top"><span className="section-label">YOUR OUTSIDE OUTLOOK</span><span className="status-pill"><span />{loading ? 'Checking' : result ? 'Current conditions' : 'Ready when you are'}</span></div>
          <div className="score-content" role="status" aria-live="polite" aria-atomic="true">
            <div className={`score-ring ${loading ? 'loading' : ''}`} style={{ '--score': `${result?.grade.score ?? 0}%` } as CSSProperties}><div className="ring-inner"><span className="score-value">{loading ? '···' : result ? Math.round(result.grade.score) : '—'}</span><span className="score-denominator">OUT OF 100</span></div></div>
            <h2>{loading ? 'Reading the conditions…' : result ? 'Your running grade is in.' : 'Your next good day starts here.'}</h2>
            <p>{loading ? 'A moment to check the weather where you’re headed.' : result ? <>Running conditions for <strong>{result.address}</strong> at {result.pace}/km.<br />The closer to 100, the better the conditions.</> : <>Choose your location and pace to see how the weather<br className="desktop-break" /> stacks up for your next run.</>}</p>
            {result && <dl className="grade-details"><div><dt>Running speed</dt><dd>{result.grade.running_speed_kph.toFixed(2)} km/h</dd></div><div><dt>Relative air speed</dt><dd>{result.grade.relative_air_speed_kph.toFixed(2)} km/h</dd></div><div><dt>Wind effort change</dt><dd>{result.grade.wind_metabolic_change_percent > 0 ? '+' : ''}{result.grade.wind_metabolic_change_percent.toFixed(2)}%</dd></div><div><dt>Temperature loss</dt><dd>{result.grade.thermal_performance_loss_percent.toFixed(2)}%</dd></div></dl>}
          </div>
          <div className="score-legend"><span>Less suitable</span><div /><span>More suitable</span></div>
          <div className="contours" aria-hidden="true" />
        </div>
      </section>

      <section className="explainer" id="how-it-works" aria-labelledby="explainer-title">
        <div className="explainer-heading"><span className="eyebrow">THE BIG PICTURE, SIMPLIFIED</span><h2 id="explainer-title">One score. A clearer way out.</h2><p>Weather is more than a temperature.<br />We bring the conditions together.</p></div>
        <div className="explanation"><span className="feature-icon"><Icon name="pin" /></span><h3>Local to your next step</h3><p>Start with an address. We find the conditions for the place you want to run.</p></div>
        <div className="explanation"><span className="feature-icon"><Icon name="wind" /></span><h3>Beyond the forecast</h3><p>Temperature, gusts, humidity, rain, and elevation shape your running score.</p></div>
        <div className="explanation"><span className="feature-icon"><Icon name="run" /></span><h3>You take it from here</h3><p>Use your score to help plan your run. Always check local alerts before heading out.</p></div>
      </section>
      <aside className="outside-note"><span aria-hidden="true">↗</span><p>The best part of your day might be outside.</p><span className="eyebrow">MAKE ROOM FOR IT.</span></aside>
    </main>}
    <footer><a className="brand footer-brand" href="#"><Icon name="wind" />windscore.</a><p>A little clarity. A little fresh air.</p><span>Built for the way you move.</span></footer>
  </>
}
