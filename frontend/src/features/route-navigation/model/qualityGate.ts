import type { RoutePoint } from '../../../api/routes/routes.api'
import type { QualityGateResult, RejectionReason } from './types'

export const FORBIDDEN_ROUTE_CATEGORIES = new Set([
  'service', 'transport', 'health', 'useful', 'pharmacy',
  'bank', 'police', 'mvd', 'atm', 'parking', 'fuel',
])

const emptyCounts = (): Record<RejectionReason, number> => ({
  missing_place_id: 0,
  missing_coordinates: 0,
  hidden_place: 0,
  route_ineligible: 0,
  service_category: 0,
})

const hasCoords = (point: RoutePoint): boolean =>
  typeof point.lat === 'number' && Number.isFinite(point.lat) &&
  typeof point.lng === 'number' && Number.isFinite(point.lng)

const hidden = (point: RoutePoint): boolean =>
  point.is_published === false ||
  point.is_active === false ||
  point.status === 'inactive' ||
  ['draft', 'hidden', 'unpublished'].includes(String(point.publication_status ?? ''))

const forbiddenCategory = (point: RoutePoint): boolean =>
  FORBIDDEN_ROUTE_CATEGORIES.has(String(point.category ?? '').toLowerCase())

export const rejectionReason = (point: RoutePoint): RejectionReason | null => {
  if (!Number.isFinite(Number(point.place_id))) return 'missing_place_id'
  if (!hasCoords(point)) return 'missing_coordinates'
  if (hidden(point)) return 'hidden_place'
  if (point.is_route_eligible === false) return 'route_ineligible'
  if (forbiddenCategory(point)) return 'service_category'
  return null
}

export const evaluateRouteQuality = (points: RoutePoint[]): QualityGateResult => {
  const counts = emptyCounts()
  const rejected = points.flatMap((point) => {
    const reason = rejectionReason(point)
    if (!reason) return []
    counts[reason] += 1
    return [{ point, reason }]
  })
  const validPoints = points
    .filter((point) => rejectionReason(point) === null)
    .map((point, index) => ({ ...point, navigationIndex: index }))

  return { validPoints, rejected, counts, canStart: validPoints.length >= 2 }
}
