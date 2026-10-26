import type { WeeklyTss } from './api'

export default function WeeklyTssCard({ data, error, onRetry }: {
  data: WeeklyTss | null; error: string; onRetry: () => void
}) {
  const formatDate = (value: string) => new Date(`${value}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  return <div className="weekly-tss" aria-label="Current week TSS">
    <span>THIS WEEK’S TSS</span>
    {error ? <><small role="alert">{error}</small><button className="grade-recalculate" type="button" onClick={onRetry}>Try again</button></>
      : !data ? <small role="status">Loading weekly TSS…</small> : <>
        <strong role="status">{data.tss === null ? '—' : data.tss.toFixed(1)}</strong>
        <small>{formatDate(data.week_start)}–{formatDate(data.week_end)} · Mon–Sun</small>
        {data.tss === null ? <small>'No TSS available.'</small>:''}
      </>}
  </div>
}
