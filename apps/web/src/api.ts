export type LocationOption = { name: string; latitude: string; longitude: string }
export type RunGrade = {
  score: number
  running_speed_kph: number
  relative_air_speed_kph: number
  wind_metabolic_change_percent: number
  thermal_performance_loss_percent: number
}

const base = (url: string) => url.replace(/\/$/, '')
const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null

export async function fetchAccessToken(baseUrl: string, username: string, password: string): Promise<string> {
  if (!username || !password) throw new Error('Enter your username and password.')
  let response: Response
  try {
    response = await fetch(`${base(baseUrl)}/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username, password }),
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

export async function fetchRunGrade(baseUrl: string, address: string, pace: string, token: string, location?: LocationOption): Promise<RunGrade | LocationOption[]> {
  if (!address.trim()) throw new Error('Enter a town, suburb, or address.')
  if (!/^\d+:[0-5]\d$/.test(pace.trim()) || /^0+:00$/.test(pace.trim())) throw new Error('Enter a pace like 5:20 per kilometre.')
  if (!token) throw new Error('Sign in to check your conditions.')
  const query = new URLSearchParams({ address: address.trim() })
  if (location) {
    query.set('latitude', location.latitude)
    query.set('longitude', location.longitude)
  }
  let response: Response
  try {
    response = await fetch(`${base(baseUrl)}/grade/run?${query}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ average_pace_minutes_per_km: pace.trim() }),
      signal: AbortSignal.timeout(30_000),
    })
  } catch {
    throw new Error('We couldn’t reach the weather service. Please try again.')
  }
  if (response.status === 401 || response.status === 403) throw new Error('Your sign-in expired. Please sign in again.')
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
