export type GeoPoint = {
  lat: number
  lng: number
  accuracy?: number | null
}

const EARTH_RADIUS_M = 6371000

const toRadians = (value: number): number => (value * Math.PI) / 180

export const haversineMeters = (from: GeoPoint, to: GeoPoint): number => {
  const dLat = toRadians(to.lat - from.lat)
  const dLng = toRadians(to.lng - from.lng)
  const fromLat = toRadians(from.lat)
  const toLat = toRadians(to.lat)
  const a = Math.sin(dLat / 2) ** 2
    + Math.cos(fromLat) * Math.cos(toLat) * Math.sin(dLng / 2) ** 2
  return EARTH_RADIUS_M * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

export const formatDistance = (meters: number | null | undefined): string | null => {
  if (meters == null || !Number.isFinite(meters)) return null
  if (meters < 1000) return `${Math.round(meters)} м`
  return `${(meters / 1000).toFixed(meters < 10000 ? 1 : 0)} км`
}
