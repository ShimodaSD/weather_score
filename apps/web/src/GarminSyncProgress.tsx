import { useEffect, useState } from 'react'
import { fetchGarminSyncProgress, type GarminSyncProgress as SyncProgress } from './api'

export function useGarminSyncProgress(baseUrl: string, token: string, syncing: boolean, onRestoredComplete: () => void) {
  const [progress, setProgress] = useState<SyncProgress | null>(null)
  const [unavailable, setUnavailable] = useState(false)

  useEffect(() => {
    setProgress(null)
    setUnavailable(false)
    if (!token) return
    let cancelled = false
    let wasActive = false
    let timer: ReturnType<typeof setTimeout>
    async function poll() {
      try {
        const next = await fetchGarminSyncProgress(baseUrl, token)
        if (!cancelled) {
          if (!syncing && wasActive && next.phase === 'complete') onRestoredComplete()
          wasActive = ['checking', 'downloading', 'importing'].includes(next.phase)
          setProgress(next)
          setUnavailable(false)
        }
      } catch {
        if (!cancelled) setUnavailable(true)
      }
      if (!cancelled) timer = setTimeout(() => { void poll() }, 30_000)
    }
    void poll()
    return () => { cancelled = true; clearTimeout(timer) }
  }, [baseUrl, token, syncing, onRestoredComplete])

  const active = progress !== null && ['checking', 'downloading', 'importing'].includes(progress.phase)
  return { progress, unavailable, active }
}

export default function GarminSyncProgress({ progress, unavailable, active, syncing }: ReturnType<typeof useGarminSyncProgress> & { syncing: boolean }) {
  if (!syncing && !active) return null
  const total = progress?.total_files
  const downloaded = progress?.downloaded_files ?? 0
  const known = total != null
  const transferring = progress?.phase === 'downloading'
  const message = unavailable ? 'Download progress is temporarily unavailable. Sync is still running.'
    : progress?.phase === 'importing' ? `${downloaded} files downloaded. Importing activities…`
      : progress?.phase === 'complete' ? `${downloaded} files downloaded. Refreshing activities…`
      : transferring && known ? `${downloaded} of ${total} files downloaded · ${total - downloaded} remaining`
        : progress?.phase === 'failed' ? 'Sync failed. Waiting for the result…'
          : 'Checking Garmin for new data…'

  return <div className="activity-sync-progress" role="status" aria-atomic="true">
    <span className="activity-sync-spinner" aria-hidden="true" />
    <div><strong>Updating your Garmin activities</strong><p>{message}</p>
      <progress aria-label="Garmin files downloaded" value={transferring && known && total > 0 ? downloaded : undefined} max={known && total > 0 ? total : undefined} />
    </div>
  </div>
}
