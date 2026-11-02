import { useState, type FormEvent } from 'react'
import { fetchRunForecast, type LocationOption, type TrainingDay } from './api'

const apiBase = import.meta.env.VITE_API_BASE_URL || '/api'

export default function TrainingDaysPage() {
  const [address, setAddress] = useState('')
  const [options, setOptions] = useState<LocationOption[]>([])
  const [selected, setSelected] = useState('')
  const [days, setDays] = useState<TrainingDay[]>([])
  const [selectedDay, setSelectedDay] = useState('')
  const [currentLocation, setCurrentLocation] = useState<LocationOption | undefined>()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function useCurrentLocation() {
    if (!navigator.geolocation) { setError('Your browser does not support location access.'); return }
    setError('')
    setLoading(true)
    navigator.geolocation.getCurrentPosition(async ({ coords }) => {
      setDays([])
      setOptions([])
      setSelected('')
      setAddress('Current location')
      const location = { name: 'Current location', latitude: String(coords.latitude), longitude: String(coords.longitude) }
      setCurrentLocation(location)
      try {
        const result = await fetchRunForecast(apiBase, 'Current location', location)
        if (result.length > 0 && 'date' in result[0]) {
          setSelectedDay('')
          setDays((result as TrainingDay[]).sort((a, b) => b.score - a.score || a.date.localeCompare(b.date)))
        } else setError('Could not find a forecast for your current location.')
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : 'Could not load the forecast.')
      } finally { setLoading(false) }
    }, () => { setLoading(false); setError('Location access was unavailable. Enter a location instead.') }, { timeout: 10000 })
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError('')
    setDays([])
    try {
      const result = await fetchRunForecast(apiBase, address, currentLocation || options[Number(selected)])
      if (result.length > 0 && 'name' in result[0]) {
        setOptions(result as LocationOption[])
        setSelected('')
      } else {
        setSelectedDay('')
        setDays([...(result as TrainingDay[])].sort((a, b) => b.score - a.score || a.date.localeCompare(b.date)))
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not load the training forecast.')
    } finally {
      setLoading(false)
    }
  }

  return <main id="main" className="training-page">
    <header className="training-hero"><span className="eyebrow"><span className="training-eyebrow-mark" /> WEATHER, MADE ACTIONABLE</span><h1>Find your <em>best days</em> to train<span className="brand-dot">.</span></h1><p>Compare the upcoming forecast and choose the best weather for your run.</p></header>
    <div className="training-workspace is-searching">
    <section className="training-search" aria-labelledby="training-search-title">
      <div className="training-search-copy"><span className="training-search-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2"/></svg></span><div><h2 id="training-search-title">Where will you train?</h2><p>We’ll compare the next seven days near you.</p></div></div>
      <form onSubmit={(event) => { void submit(event) }}>
        <div className="training-field"><label htmlFor="training-location">Town, city, or address</label><div className="training-location-control"><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2"/></svg><input className="text-field" id="training-location" value={address} onChange={(event) => { setAddress(event.target.value); setCurrentLocation(undefined); setOptions([]); setSelected(''); setDays([]) }} maxLength={300} required disabled={loading} placeholder="e.g. São Paulo, Brazil" /></div></div>
        {options.length > 0 && <div className="training-field training-choice"><label htmlFor="training-location-choice">Choose a matching neighbourhood</label><select id="training-location-choice" value={selected} onChange={(event) => { setSelected(event.target.value); setDays([]) }} required disabled={loading}><option value="">Select a location</option>{options.map((option, index) => <option value={index} key={`${option.latitude},${option.longitude}`}>{option.name}</option>)}</select></div>}
        <button className="submit" type="submit" disabled={loading}>{loading ? 'Checking forecast…' : options.length ? days.length ? 'Update forecast' : 'Use this neighbourhood' : 'Find my best training days'}</button>
        <button className="training-use-location" type="button" disabled={loading} onClick={useCurrentLocation}><svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2"/></svg>Use my current location</button>
        {error && <p className="error-message" role="alert">{error}</p>}
      </form>
    </section>
    {days.length > 0 ? <section className="training-results" aria-labelledby="training-results-title">
      <div className="training-results-heading"><div><span className="eyebrow">{days.length}-DAY OUTLOOK</span><h2 id="training-results-title">Your training forecast</h2></div><p>Ranked by weather suitability</p></div>
      <div className="forecast-panels"><div className="forecast-list"><h3>Best days</h3><p>Select a day to see its grade.</p><ol>{days.map((day, index) => <li key={day.date}><button type="button" className="forecast-day" aria-pressed={(selectedDay || days[0].date) === day.date} onClick={() => setSelectedDay(day.date)}><span className="forecast-rank">{index === 0 ? 'BEST' : String(index + 1).padStart(2, '0')}</span><span>{new Date(`${day.date}T12:00:00`).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}</span><strong>{Math.round(day.score)}<small> / 100</small></strong></button></li>)}</ol></div>
      {(() => { const day = days.find((item) => item.date === selectedDay) || days[0]; return <aside className="forecast-detail" aria-live="polite"><span className="eyebrow">DAY BREAKDOWN</span><h3>{new Date(`${day.date}T12:00:00`).toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' })}</h3><div className="forecast-grade"><strong>{Math.round(day.score)}</strong><span>/ 100<br />weather score</span></div><p>Impact on your score</p>{day.temperature_c === undefined ? <p>Detailed impacts are unavailable for this forecast.</p> : <dl>{[['Temperature', `${day.temperature_c?.toFixed(1)} °C`, day.temperature_penalty], ['Wind gusts', `${day.wind_gust_kph?.toFixed(1)} km/h`, day.wind_penalty], ['Humidity', `${day.humidity_percent?.toFixed(0)}%`, day.humidity_penalty], ['Precipitation', `${day.precipitation_mm?.toFixed(1)} mm`, day.precipitation_penalty], ['Elevation', `${day.altitude_m?.toFixed(0)} m`, day.altitude_penalty]].map(([label, value, penalty]) => <div key={String(label)}><dt>{label}</dt><dd>{value} <strong>−{typeof penalty === 'number' ? penalty.toFixed(2) : '—'}</strong></dd></div>)}</dl>}<small>Points deducted from 100; score is capped at zero.</small></aside> })()}</div>
      <p className="training-disclaimer">A planning guide based on forecast weather. Check local conditions and alerts before heading out.</p>
    </section> : <section className="training-results training-results-empty" aria-labelledby="training-empty-title" aria-live="polite"><div className="training-results-heading"><div><span className="eyebrow">7-DAY OUTLOOK</span><h2 id="training-empty-title">Your training forecast</h2></div></div><div className="forecast-panels"><div className="forecast-list"><h3>Best days</h3><p>{loading ? 'Checking the forecast…' : error ? 'Forecast unavailable. Try another location.' : 'Search for a location to load the forecast. Values below are placeholders.'}</p><ol>{Array.from({ length: 7 }, (_, index) => <li key={index}><div className="forecast-day forecast-placeholder"><span className="forecast-rank">{String(index + 1).padStart(2, '0')}</span><span>Day {index + 1}</span><strong>0 <small>/ 100</small></strong></div></li>)}</ol></div><div className="forecast-detail"><span className="eyebrow">DAY BREAKDOWN</span><h3>Weather score</h3><div className="forecast-grade"><strong>0</strong><span>/ 100<br />weather score</span></div><p>Waiting for forecast</p><dl>{[['Temperature', '0 °C'], ['Wind gusts', '0 km/h'], ['Humidity', '0%'], ['Precipitation', '0 mm'], ['Elevation', '0 m']].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value} <strong>−0.00</strong></dd></div>)}</dl></div></div></section>}
    </div>
  </main>
}
