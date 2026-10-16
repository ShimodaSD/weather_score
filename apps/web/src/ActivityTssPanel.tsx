import { useEffect, useState } from 'react'
import { fetchActivityTss, type ActivityTss } from './api'

export default function ActivityTssPanel({ id, sport, token, onTokenChange, showProfileLink = true }: {
  id: string; sport: string; token: string; onTokenChange: (token: string) => void; showProfileLink?: boolean
}) {
  const [result, setResult] = useState<ActivityTss | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  const supported = sport === 'running' || sport === 'cycling'

  useEffect(() => {
    if (!supported || !token) return
    let cancelled = false
    setResult(null)
    setLoading(true)
    setError('')
    fetchActivityTss(import.meta.env.VITE_API_BASE_URL || '/api', id, token).then((data) => {
      if (!cancelled) setResult(data)
    }).catch((reason) => {
      if (cancelled) return
      if (reason instanceof Error && reason.message.includes('sign-in expired')) onTokenChange('')
      setError(reason instanceof Error ? reason.message : 'Could not calculate TSS.')
    }).finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [id, token, supported, onTokenChange, retry])

  return <section className="full-detail-section tss-panel" aria-labelledby="tss-title">
    <div className="full-detail-section-head"><h2 id="tss-title">Training stress score</h2></div>
    {!supported ? <p>TSS is currently available for running and cycling.</p> : loading ? <p role="status">Calculating training stress…</p> : error ? <>
      <p className="error-message" role="alert">{error}</p>
      <button className="grade-recalculate" type="button" onClick={() => setRetry((count) => count + 1)}>Try again</button>
    </> : result && <>
      <p role="status"><strong>{result.tss.toFixed(1)} estimated TSS</strong> · Threshold {result.threshold} bpm · {(result.duration_seconds / 60).toFixed(1)} minutes</p>
      <p>100 points represents one hour at your threshold. Longer or harder activities can exceed 100.</p>
      {result.warnings.map((warning) => <p key={warning}>{warning}</p>)}
    </>}
    {showProfileLink && <a className="full-detail-link" href="#profile">Edit your threshold in Profile <span aria-hidden="true">→</span></a>}
  </section>
}
