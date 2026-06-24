import { LOCATION_STALE_MS } from './config'
import type { LocationCoordinates, LocationSnapshot, LocationSource } from './types'

export const validCoordinate = (latitude: number, longitude: number): boolean =>
  Number.isFinite(latitude)
  && Number.isFinite(longitude)
  && latitude >= -90
  && latitude <= 90
  && longitude >= -180
  && longitude <= 180
  && !(latitude === 0 && longitude === 0)

export const createSnapshot = (
  coordinates: LocationCoordinates,
  source: LocationSource,
  capturedAt = Date.now(),
): LocationSnapshot => ({
  coordinates,
  source,
  capturedAt,
  stale: Date.now() - capturedAt > LOCATION_STALE_MS,
})

export const browserSnapshot = (
  position: GeolocationPosition,
  source: LocationSource = 'browser',
): LocationSnapshot => createSnapshot({
  accuracy: position.coords.accuracy,
  altitude: position.coords.altitude,
  course: position.coords.heading,
  latitude: position.coords.latitude,
  longitude: position.coords.longitude,
  speed: position.coords.speed,
}, source, position.timestamp || Date.now())
