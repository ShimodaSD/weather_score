import { useRef, useState, type FormEvent, type CSSProperties } from 'react'
import { fetchRunningScore } from './api'

function Icon({ name, className = '' }: { name: 'wind' | 'arrow' | 'pin' | 'run' | 'bike' | 'sun'; className?: string }) {
  const paths = {
    wind: <><path d="M3 8h12a3 3 0 1 0-3-3M3 12h16a3 3 0 1 1-3 3M3 16h6a3 3 0 1 1-3 3" /></>,
    arrow: <><path d="M4 12h15m-6-6 6 6-6 6" /></>,
    pin: <><path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z" /><circle cx="12" cy="10" r="2" /></>,
    run: <><circle cx="15" cy="4" r="2" /><path d="m5 10 5-3 4 3 5 1m-9-4-2 7 5 3-1 5m-4-8-3 5H2" /></>,
    bike: <><circle cx="5" cy="17" r="4" /><circle cx="19" cy="17" r="4" /><path d="m5 17 5-9 6 9H5m11 0-3-12h4M8 8h5" /></>,
    sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5" /></>,
  }
  return <svg className={className} width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>
}

export default function App() {
  const [address, setAddress] = useState('')
  const [result, setResult] = useState<{ score: number; address: string } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const busy = useRef(false)

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
      const score = await fetchRunningScore(import.meta.env.VITE_API_BASE_URL || '/api', location)
      setResult({ score, address: location })
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Something went wrong. Please try again.')
    } finally {
      busy.current = false
      setLoading(false)
    }
  }

  return <>
    <a className="skip-link" href="#main">Skip to content</a>
    <header className="header">
      <a className="brand" href="#" aria-label="Wind Score home"><span className="brand-mark"><Icon name="wind" /></span>windscore<span className="brand-dot">.</span></a>
      <nav aria-label="Main navigation"><a className="nav-active" href="#check">Conditions</a><a href="#how-it-works">How it works <span aria-hidden="true">↗</span></a></nav>
      <span className="header-note"><span /> Made for the outdoors</span>
    </header>

    <main id="main">
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
            <div className={`location-input ${error ? 'input-error' : ''}`}><Icon name="pin" /><input id="address" name="address" placeholder="Town, suburb, or street address" value={address} onChange={(event) => setAddress(event.target.value)} required maxLength={300} disabled={loading} aria-describedby={error ? 'location-hint search-error' : 'location-hint'} /></div>
            <p id="location-hint" className="field-hint">Add your city or country for a more accurate match.</p>
            <fieldset><legend>Your activity</legend><div className="activities"><div className="activity selected"><Icon name="run" /><span>Running</span><span className="selection-dot" aria-label="Selected" /></div><div className="activity unavailable"><Icon name="bike" /><span>Cycling</span><span className="soon">Soon</span></div></div></fieldset>
            <button className="submit" type="submit" disabled={loading}>{loading ? 'Checking conditions…' : 'Check my conditions'}<Icon name="arrow" /></button>
            {error && <p className="error-message" id="search-error" role="alert">{error}</p>}
            <p className="form-note">Your location is only used to find your conditions.</p>
          </form>
          <div className="planner-bottom"><span className="small-wind"><Icon name="wind" /></span><p>A little headwind shouldn’t be a guessing game.</p></div>
        </div>

        <div className="score-panel" aria-busy={loading}>
          <div className="score-top"><span className="section-label">YOUR OUTSIDE OUTLOOK</span><span className="status-pill"><span />{loading ? 'Checking' : result ? 'Current conditions' : 'Ready when you are'}</span></div>
          <div className="score-content" role="status" aria-live="polite" aria-atomic="true">
            <div className={`score-ring ${loading ? 'loading' : ''}`} style={{ '--score': `${result?.score ?? 0}%` } as CSSProperties}><div className="ring-inner"><span className="score-value">{loading ? '···' : result ? Math.round(result.score) : '—'}</span><span className="score-denominator">OUT OF 100</span></div></div>
            <h2>{loading ? 'Reading the conditions…' : result ? 'Your running score is in.' : 'Your next good day starts here.'}</h2>
            <p>{loading ? 'A moment to check the weather where you’re headed.' : result ? <>Running conditions for <strong>{result.address}</strong>.<br />The closer to 100, the better the conditions.</> : <>Choose your location to see how the weather<br className="desktop-break" /> stacks up for your next run.</>}</p>
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
    </main>
    <footer><a className="brand footer-brand" href="#"><Icon name="wind" />windscore.</a><p>A little clarity. A little fresh air.</p><span>Built for the way you move.</span></footer>
  </>
}
