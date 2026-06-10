import type { CityOption } from '../../shared/city/currentCity'
import { buildApiUrl } from '../../shared/api/http'

type CitiesResponse = CityOption[] | {
  items?: CityOption[]
}

export const getAvailableCities = async (): Promise<CityOption[]> => {
  const response = await fetch(buildApiUrl('/cities/available?include_draft=true'))

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  const data: CitiesResponse = await response.json()

  if (Array.isArray(data)) {
    return data
  }

  if (Array.isArray(data.items)) {
    return data.items
  }

  return []
}
