export type ChartPoint = { x: number; y: number | null }
export const PACE_ZONES = [
  { name: 'Trote', fastSeconds: 450, slowSeconds: 540, color: '#dce5e7' },
  { name: 'Zona 0', fastSeconds: 386, slowSeconds: 450, color: '#e5eed7' },
  { name: 'Zona 1', fastSeconds: 346, slowSeconds: 386, color: '#d5e9c5' },
  { name: 'Zona 2', fastSeconds: 307, slowSeconds: 346, color: '#c3e2b5' },
  { name: 'Zona 3', fastSeconds: 284, slowSeconds: 307, color: '#b0d9aa' },
  { name: 'Zona 4', fastSeconds: 270, slowSeconds: 284, color: '#9ccfa1' },
  { name: 'Zona 5', fastSeconds: 250, slowSeconds: 270, color: '#88c49a' },
  { name: 'Zona 6', fastSeconds: 225, slowSeconds: 250, color: '#75b993' },
] as const
export const MAX_PACE_MIN_PER_KM = PACE_ZONES[0].slowSeconds / 60
export const MIN_PACE_MIN_PER_KM = PACE_ZONES.at(-1)!.fastSeconds / 60

export function paceZoneName(minutesPerKm: number): string {
  const seconds = minutesPerKm * 60
  if (seconds >= PACE_ZONES[0].slowSeconds) return 'Trote or slower / no speed'
  return PACE_ZONES.find((zone) => seconds >= zone.fastSeconds && seconds < zone.slowSeconds)?.name ?? 'Zona 6'
}

export function buildLapMarkers(laps: Record<string, unknown>[], startedAt: string, elapsedSeconds: number): { x: number; label: string }[] {
  const activityStart = Date.parse(startedAt)
  if (!Number.isFinite(activityStart)) return []
  return laps.flatMap((lap, index) => {
    const start = typeof lap.start_time === 'string' ? Date.parse(lap.start_time) : NaN
    const duration = typeof lap.elapsed_time === 'string' ? /^(\d{1,2}):([0-5]\d):([0-5]\d)(?:\.(\d+))?$/.exec(lap.elapsed_time) : null
    if (!Number.isFinite(start) || !duration) return []
    const seconds = (start - activityStart) / 1000 + Number(duration[1]) * 3600 + Number(duration[2]) * 60 + Number(duration[3]) + Number(`0.${duration[4] ?? '0'}`)
    if (seconds <= 0 || seconds > elapsedSeconds + 1) return []
    return [{ x: Math.min(seconds, elapsedSeconds) / 60, label: String(index + 1) }]
  })
}

export function buildActivitySeries(records: Record<string, unknown>[], startedAt: string): { heartRate: ChartPoint[]; pace: ChartPoint[]; adjustedPace: ChartPoint[]; xUnit: 'minutes' | 'samples' } {
  const firstTimestamp = records.find((record) => typeof record.timestamp === 'string' && Number.isFinite(Date.parse(record.timestamp)))?.timestamp
  const activityStart = Date.parse(startedAt)
  const firstTime = typeof firstTimestamp === 'string' ? Number.isFinite(activityStart) ? activityStart : Date.parse(firstTimestamp) : null
  const heartRate: ChartPoint[] = []
  const pace: ChartPoint[] = []
  const adjustedPace: ChartPoint[] = []
  let elevationWindow: { distance: number; altitude: number; gain: number }[] = []

  records.forEach((record, index) => {
    const timestamp = typeof record.timestamp === 'string' ? Date.parse(record.timestamp) : NaN
    if (firstTime !== null && !Number.isFinite(timestamp)) return
    const x = firstTime === null ? index : (timestamp - firstTime) / 60_000
    const hr = record.hr
    const speed = record.speed
    heartRate.push({ x, y: typeof hr === 'number' && Number.isFinite(hr) && hr > 0 ? hr : null })
    const minutesPerKm = typeof speed === 'number' && Number.isFinite(speed) && speed > 0 ? 60 / speed : MAX_PACE_MIN_PER_KM
    pace.push({ x, y: Math.min(minutesPerKm, MAX_PACE_MIN_PER_KM) })
    const distance = record.distance
    const altitude = record.altitude
    let adjusted: number | null = null
    if (typeof distance === 'number' && Number.isFinite(distance) && distance >= 0
      && typeof altitude === 'number' && Number.isFinite(altitude)) {
      const previous = elevationWindow.at(-1)
      if (previous && distance < previous.distance) elevationWindow = []
      if (!previous || distance !== previous.distance) {
        const last = elevationWindow.at(-1)
        const gain = (last?.gain ?? 0) + (last ? Math.max(0, altitude - last.altitude) : 0)
        elevationWindow.push({ distance, altitude, gain })
        while (elevationWindow.length > 1 && distance - elevationWindow[1].distance >= 0.1) elevationWindow.shift()
        const horizontalMeters = (distance - elevationWindow[0].distance) * 1000
        if (horizontalMeters >= 50 && typeof speed === 'number' && Number.isFinite(speed) && speed > 0) {
          const uphillMeters = gain - elevationWindow[0].gain
          adjusted = 60 / (speed * (1 + 10 * uphillMeters / horizontalMeters))
        }
      }
    } else elevationWindow = []
    adjustedPace.push({ x, y: adjusted })
  })

  return { heartRate, pace, adjustedPace, xUnit: firstTime === null ? 'samples' : 'minutes' }
}
