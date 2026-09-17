export type LocationOption = { name: string; latitude: string; longitude: string }
export type RunGrade = {
  score: number
  running_speed_kph: number
  relative_air_speed_kph: number
  wind_metabolic_change_percent: number
  thermal_performance_loss_percent: number
}
export type Activity = {
  activity_id: string
  activity_type: string
  name: string | null
  started_at: string
  elapsed_seconds: number
  moving_seconds: number | null
  distance_km: number | null
  average_pace_seconds_per_km: number | null
  average_speed_kph: number | null
  average_heart_rate_bpm: number | null
  maximum_heart_rate_bpm: number | null
  calories: number | null
  average_cadence_per_minute: number | null
  elevation_gain_m: number | null
  elevation_loss_m: number | null
  average_temperature_c: number | null
  training_effect: number | null
  anaerobic_training_effect: number | null
}
export type ActivityIndex = Pick<Activity, 'activity_id' | 'activity_type' | 'name' | 'started_at'>
export type ActivityDetail = Activity & {
  activity: Record<string, unknown>
  laps: Record<string, unknown>[]
  splits: Record<string, unknown>[]
  records: Record<string, unknown>[]
  devices: Record<string, unknown>[]
}
export type RunningPrediction = {
  distance_km: number
  predicted_seconds: number | null
  low_seconds: number
  high_seconds: number
}
export type RunningPredictionBasis = {
  distance_km: number
  moving_seconds: number
  source_activity_id: string
  source_distance_km: number
  source_started_at: string
}
export type RunningPredictions = {
  run_count: number
  longest_run_km: number | null
  season_start_at: string | null
  season_end_at: string | null
  model_status: 'fitted' | 'range' | 'no_benchmark'
  vm_mps: number | null
  endurance_index: number | null
  basis: RunningPredictionBasis[]
  predictions: RunningPrediction[]
}

const base = (url: string) => url.replace(/\/$/, '')
export const SESSION_AUTH = 'cookie-session'
const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null
const isIndex = (item: unknown): item is ActivityIndex & Record<string, unknown> => isRecord(item)
  && typeof item.activity_id === 'string' && typeof item.activity_type === 'string'
  && typeof item.started_at === 'string' && Number.isFinite(Date.parse(item.started_at))
  && (item.name === null || typeof item.name === 'string')
const activityNumbers = ['moving_seconds', 'distance_km', 'average_pace_seconds_per_km', 'average_speed_kph',
  'average_heart_rate_bpm', 'maximum_heart_rate_bpm', 'calories', 'average_cadence_per_minute',
  'elevation_gain_m', 'elevation_loss_m', 'average_temperature_c', 'training_effect', 'anaerobic_training_effect']
const isActivity = (item: unknown): item is Activity & Record<string, unknown> => isIndex(item)
  && typeof item.elapsed_seconds === 'number' && Number.isFinite(item.elapsed_seconds)
  && activityNumbers.every((key) => item[key] === null || typeof item[key] === 'number' && Number.isFinite(item[key]))

async function fetchActivityJson(baseUrl: string, path: string, token: string): Promise<unknown> {
  if (!token) throw new Error('Sign in to see your activities.')
  let response: Response
  try {
    response = await fetch(`${base(baseUrl)}${path}`, {
      headers: token === SESSION_AUTH ? {} : { Authorization: `Bearer ${token}` },
      credentials: 'include',
      signal: AbortSignal.timeout(30_000),
    })
  } catch {
    throw new Error('We couldn’t reach the activity service. Please try again.')
  }
  if (response.status === 401 || response.status === 403) throw new Error('Your sign-in expired. Please sign in again.')
  if (response.status === 404) throw new Error('Activity not found.')
  if (!response.ok) throw new Error('Activities are unavailable right now. Please try again shortly.')
  return response.json().catch(() => null)
}

export async function fetchActivityIndex(baseUrl: string, token: string): Promise<ActivityIndex[]> {
  const data = await fetchActivityJson(baseUrl, '/activities/index', token)
  if (!Array.isArray(data) || !data.every(isIndex)) throw new Error('The service returned an unexpected activity response.')
  return data
}

export async function fetchActivitySummary(baseUrl: string, id: string, token: string): Promise<Activity> {
  const data = await fetchActivityJson(baseUrl, `/activities/${encodeURIComponent(id)}/summary`, token)
  if (!isActivity(data)) {
    throw new Error('The service returned an unexpected activity response.')
  }
  return data as Activity
}

export async function fetchActivityDetail(baseUrl: string, id: string, token: string): Promise<ActivityDetail> {
  const data = await fetchActivityJson(baseUrl, `/activities/${encodeURIComponent(id)}`, token)
  if (!isActivity(data) || !isRecord(data.activity)
    || !['laps', 'splits', 'records', 'devices'].every((key) => Array.isArray(data[key]) && data[key].every(isRecord))) {
    throw new Error('The service returned an unexpected activity response.')
  }
  return data as ActivityDetail
}

export async function fetchRunningPredictions(baseUrl: string, token: string): Promise<RunningPredictions> {
  const data = await fetchActivityJson(baseUrl, '/activities/running/predictions', token)
  if (!isRecord(data) || typeof data.run_count !== 'number' || !Number.isInteger(data.run_count) || data.run_count < 0
    || !(data.longest_run_km === null || typeof data.longest_run_km === 'number' && Number.isFinite(data.longest_run_km) && data.longest_run_km > 0)
    || !['fitted', 'range', 'no_benchmark'].includes(String(data.model_status))
    || ![data.season_start_at, data.season_end_at].every((value) => value === null || typeof value === 'string' && Number.isFinite(Date.parse(value)))
    || ![data.vm_mps, data.endurance_index].every((value) => value === null || typeof value === 'number' && Number.isFinite(value) && value > 0)
    || !Array.isArray(data.basis) || !data.basis.every((item) => isRecord(item)
      && typeof item.distance_km === 'number' && Number.isFinite(item.distance_km) && item.distance_km > 0
      && typeof item.moving_seconds === 'number' && Number.isFinite(item.moving_seconds) && item.moving_seconds > 0
      && typeof item.source_activity_id === 'string'
      && typeof item.source_distance_km === 'number' && Number.isFinite(item.source_distance_km) && item.source_distance_km > 0
      && typeof item.source_started_at === 'string' && Number.isFinite(Date.parse(item.source_started_at)))
    || !Array.isArray(data.predictions) || !data.predictions.every((item) => isRecord(item)
      && typeof item.distance_km === 'number' && Number.isFinite(item.distance_km) && item.distance_km > 0
      && (item.predicted_seconds === null || typeof item.predicted_seconds === 'number' && Number.isFinite(item.predicted_seconds) && item.predicted_seconds > 0)
      && typeof item.low_seconds === 'number' && Number.isFinite(item.low_seconds) && item.low_seconds > 0
      && typeof item.high_seconds === 'number' && Number.isFinite(item.high_seconds) && item.high_seconds >= item.low_seconds)) {
    throw new Error('The service returned an unexpected prediction response.')
  }
  return data as RunningPredictions
}

export async function fetchAccessToken(baseUrl: string, username: string, password: string): Promise<string> {
  if (!username || !password) throw new Error('Enter your username and password.')
  let response: Response
  try {
    response = await fetch(`${base(baseUrl)}/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username, password }),
      credentials: 'include',
      signal: AbortSignal.timeout(30_000),
    })
  } catch {
    throw new Error('We couldn’t reach the weather service. Please try again.')
  }
  if (response.status === 401) throw new Error('Incorrect username or password.')
  if (!response.ok) throw new Error('Sign-in is unavailable right now. Please try again shortly.')
  const data: unknown = await response.json().catch(() => null)
  if (!isRecord(data) || typeof data.access_token !== 'string' || !data.access_token) {
    throw new Error('The service returned an unexpected response. Please try again later.')
  }
  return data.access_token
}

export async function hasSession(baseUrl: string): Promise<boolean> {
  try {
    const response = await fetch(`${base(baseUrl)}/session`, { credentials: 'include' })
    return response.ok
  } catch {
    return false
  }
}

export async function endSession(baseUrl: string): Promise<void> {
  const response = await fetch(`${base(baseUrl)}/logout`, { method: 'POST', credentials: 'include' })
  if (!response.ok) throw new Error('Could not sign out. Please try again.')
}

export async function fetchRunGrade(baseUrl: string, address: string, pace: string, location?: LocationOption): Promise<RunGrade | LocationOption[]> {
  if (!address.trim()) throw new Error('Enter a town, suburb, or address.')
  if (!/^\d+:[0-5]\d$/.test(pace.trim()) || /^0+:00$/.test(pace.trim())) throw new Error('Enter a pace like 5:20 per kilometre.')
  const query = new URLSearchParams({ address: address.trim() })
  if (location) {
    query.set('latitude', location.latitude)
    query.set('longitude', location.longitude)
  }
  let response: Response
  try {
    response = await fetch(`${base(baseUrl)}/grade/run?${query}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ average_pace_minutes_per_km: pace.trim() }),
      signal: AbortSignal.timeout(30_000),
    })
  } catch {
    throw new Error('We couldn’t reach the weather service. Please try again.')
  }
  if (response.status === 422) throw new Error('Check your address and pace, then try again.')
  if (!response.ok) throw new Error('Conditions are unavailable right now. Please try again shortly.')
  const data: unknown = await response.json().catch(() => null)
  if (isRecord(data) && typeof data.error === 'string') {
    throw new Error('We couldn’t find conditions for that address. Try a nearby town or a more specific address.')
  }
  if (isRecord(data) && Array.isArray(data.options) && data.options.length > 0
    && data.options.every((option): option is LocationOption => isRecord(option)
      && typeof option.name === 'string' && typeof option.latitude === 'string' && typeof option.longitude === 'string')) {
    return data.options
  }
  if (!isRecord(data) || !['score', 'running_speed_kph', 'relative_air_speed_kph', 'wind_metabolic_change_percent', 'thermal_performance_loss_percent']
    .every((key) => typeof data[key] === 'number' && Number.isFinite(data[key]))) {
    throw new Error('The service returned an unexpected response. Please try again later.')
  }
  if ((data.score as number) < 0 || (data.score as number) > 100 || (data.running_speed_kph as number) <= 0
    || (data.relative_air_speed_kph as number) < 0 || (data.thermal_performance_loss_percent as number) < 0) {
    throw new Error('The service returned an unexpected response. Please try again later.')
  }
  return data as RunGrade
}
