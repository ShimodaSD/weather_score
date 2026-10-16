import { useEffect, useState } from 'react'
import { fetchWeeklyTss, type WeeklyTss } from './api'

export default function WeeklyTssCard({ token, onTokenChange }: {
  token: string; onTokenChange: (token: string) => void
}) {
  const [data, setData] = useState<WeeklyTss | null>(null)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    let cancelled = false
    setData(null)
    setError('')
    fetchWeeklyTss(import.meta.env.VITE_API_BASE_URL || '/api', token).then((result) => {
      if (!cancelled) setData(result)
    }).catch((reason) => {
      if (cancelled) return
      if (reason instanceof Error && reason.message.includes('sign-in expired')) onTokenChange('')
      setError(reason instanceof Error ? reason.message : 'Could not load weekly TSS.')
    })
    return () => { cancelled = true }
  }, [token, onTokenChange, retry])

  const formatDate = (value: string) => new Date(`${value}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  return <div className="weekly-tss" aria-label="Current week TSS">
    <span>THIS WEEK’S TSS</span>
    {error ? <><small role="alert">{error}</small><button className="grade-recalculate" type="button" onClick={() => setRetry((count) => count + 1)}>Try again</button></>
      : !data ? <small role="status">Loading weekly TSS…</small> : <>
        <strong role="status">{data.tss === null ? '—' : data.tss.toFixed(1)}</strong>
        <small>{formatDate(data.week_start)}–{formatDate(data.week_end)} · Mon–Sun</small>
        {data.tss === null ? <small>'No TSS available.'</small>:''}
      </>}
  </div>
}
