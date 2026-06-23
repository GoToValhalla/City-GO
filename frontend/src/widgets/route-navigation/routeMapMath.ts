import type { NavigationPoint } from '../../features/route-navigation/model/types'

export type MapPoint = NavigationPoint & { x: number; y: number }

export const normalizePointsForMap = (points: NavigationPoint[]): MapPoint[] => {
  const valid = points.filter((point) => Number.isFinite(point.lat) && Number.isFinite(point.lng))
  if (valid.length === 0) return []
  const minLat = Math.min(...valid.map((point) => Number(point.lat)))
  const maxLat = Math.max(...valid.map((point) => Number(point.lat)))
  const minLng = Math.min(...valid.map((point) => Number(point.lng)))
  const maxLng = Math.max(...valid.map((point) => Number(point.lng)))
  const latSpan = Math.max(maxLat - minLat, 0.00001)
  const lngSpan = Math.max(maxLng - minLng, 0.00001)

  return valid.map((point) => ({
    ...point,
    x: 8 + ((Number(point.lng) - minLng) / lngSpan) * 84,
    y: 92 - ((Number(point.lat) - minLat) / latSpan) * 84,
  }))
}

export const routePath = (points: MapPoint[]): string =>
  points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`).join(' ')
