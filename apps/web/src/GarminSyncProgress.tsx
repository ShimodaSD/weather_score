import { useEffect, useRef, useState } from 'react'
import { fetchGarminSyncProgress, type GarminSyncProgress as SyncProgress } from './api'

export function useGarminSyncProgress(baseUrl: string, token: string, syncing: boolean, onComplete: () => void) {
  const [progress, setProgress] = useState<SyncProgress | null>(null)
  const [unavailable, setUnavailable] = useState(false)

  const wasActive = useRef(false)

  useEffect(() => {
    if (syncing) wasActive.current = true
  }, [syncing])

  useEffect(() => {
    setProgress(null)
    setUnavailable(false)
    if (!token) return
    let cancelled = false
    let timer: ReturnType<typeof setTimeout>
    async function poll() {
      try {
        const next = await fetchGarminSyncProgress(baseUrl, token)
        if (!cancelled) {
          if (wasActive.current && next.phase === 'complete') onComplete()
          wasActive.current = ['checking', 'downloading', 'importing'].includes(next.phase)
          setProgress(next)
          setUnavailable(false)
        }
      } catch {
        if (!cancelled) setUnavailable(true)
      }
      if (!cancelled) timer = setTimeout(() => { void poll() }, wasActive.current ? 2_000 : 30_000)
    }
    void poll()
    return () => { cancelled = true; wasActive.current = false; clearTimeout(timer) }
  }, [baseUrl, token, onComplete])

  const active = progress !== null && ['checking', 'downloading', 'importing'].includes(progress.phase)
  return { progress, unavailable, active }
}

export default function GarminSyncProgress({ progress, unavailable, active, syncing }: ReturnType<typeof useGarminSyncProgress> & { syncing: boolean }) {
  if (!syncing && !active) return null
  const total = progress?.total_files
  const downloaded = progress?.downloaded_files ?? 0
  const known = total != null
  const transferring = progress?.phase === 'downloading'
  const percentage = transferring && known && total > 0 && !unavailable ? Math.round(downloaded / total * 100) : null
  const phase = progress?.phase ?? 'checking'
  const steps = ['Checking', 'Downloading', 'Importing', 'Complete']
  const currentStep = ['checking', 'downloading', 'importing', 'complete'].indexOf(phase)
  const message = unavailable ? 'Download progress is temporarily unavailable. Sync is still running.'
    : progress?.phase === 'importing' ? `${downloaded} files downloaded. Importing activities…`
      : progress?.phase === 'complete' ? `${downloaded} files downloaded. Refreshing activities…`
      : transferring && known ? `${downloaded} of ${total} files downloaded · ${total - downloaded} remaining`
        : progress?.phase === 'failed' ? 'Sync failed. Waiting for the result…'
          : 'Checking Garmin for new data…'

  return <div className="activity-sync-progress" role="status" aria-atomic="true">
    <div className="activity-sync-heading"><strong>Updating your Garmin activities</strong><span className="activity-sync-percentage">{percentage === null ? 'Syncing…' : `${percentage}%`}</span></div>
    <div className={`activity-sync-track${percentage === null ? ' is-indeterminate' : ''}`}>
      <progress aria-label="Garmin files downloaded" value={percentage === null ? undefined : downloaded} max={known && total > 0 ? total : undefined} />
    </div>
    <p>{message}</p>
    <ol className="activity-sync-steps" aria-label="Sync stages">{steps.map((step, index) => {
      const complete = currentStep > index
      const current = currentStep === index
      return <li key={step} className={complete ? 'is-complete' : current ? 'is-current' : ''} aria-current={current ? 'step' : undefined}>
        <span className={`activity-sync-step-icon${current ? ' activity-sync-spinner' : ''}`} aria-hidden="true">{complete ? '✓' : index + 1}</span><span>{step}</span>
      </li>
    })}</ol>
  </div>
}
