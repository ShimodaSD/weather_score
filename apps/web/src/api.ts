export type LocationOption = { name: string; latitude: string; longitude: string }

export async function fetchRunningScore(baseUrl: string, address: string, location?: LocationOption): Promise<number | LocationOption[]> {
  if (!address.trim()) throw new Error('Enter a town, suburb, or address.')
  let response: Response
  try {
    const query = new URLSearchParams({ address: address.trim() })
    if (location) {
      query.set('latitude', location.latitude)
      query.set('longitude', location.longitude)
    }
    response = await fetch(`${baseUrl.replace(/\/$/, '')}/score/run?${query}`, {
      signal: AbortSignal.timeout(30_000),
    })
  } catch {
    throw new Error('We couldn’t reach the weather service. Please try again.')
  }
  if (response.status === 401 || response.status === 403) {
    throw new Error('The service requires authentication. Please contact the site administrator.')
  }
  if (!response.ok) throw new Error('Conditions are unavailable right now. Please try again shortly.')
  const data: unknown = await response.json().catch(() => null)
  if (typeof data === 'object' && data !== null && 'error' in data) {
    throw new Error('We couldn’t find conditions for that address. Try a nearby town or a more specific address.')
  }
  if (typeof data === 'object' && data !== null && 'options' in data && Array.isArray(data.options)
    && data.options.every((option): option is LocationOption => typeof option === 'object' && option !== null
      && typeof option.name === 'string' && typeof option.latitude === 'string' && typeof option.longitude === 'string')) {
    return data.options
  }
  if (typeof data !== 'number' || !Number.isFinite(data) || data < 0 || data > 100) {
    throw new Error('The service returned an unexpected response. Please try again later.')
  }
  return data
}
