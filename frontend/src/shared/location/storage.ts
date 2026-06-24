import { LOCATION_TTL_MS } from './config'
import type { LocationSnapshot } from './types'

const KEY = 'citygo:temporary-location'

export const saveLocationSnapshot = (snapshot: LocationSnapshot): void => {
  sessionStorage.setItem(KEY, JSON.stringify(snapshot))
}

export const restoreLocationSnapshot = (): LocationSnapshot | null => {
  const raw = sessionStorage.getItem(KEY)
  if (!raw) return null
  try {
    const snapshot = JSON.parse(raw) as LocationSnapshot
    if (Date.now() - snapshot.capturedAt <= LOCATION_TTL_MS) return snapshot
  } catch {
    // Invalid temporary state is removed below.
  }
  sessionStorage.removeItem(KEY)
  return null
}

export const clearLocationSnapshot = (): void => sessionStorage.removeItem(KEY)
