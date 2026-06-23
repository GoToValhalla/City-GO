import type { RoutePoint } from '../../../api/routes/routes.api'

export type RouteNavigationStatus = 'not_started' | 'active' | 'completed'

export type RouteNavigationState = {
  status: RouteNavigationStatus
  currentPointIndex: number
  visitedPointIds: number[]
}

export type RouteNavigationEvent =
  | { type: 'START_ROUTE' }
  | { type: 'MARK_CURRENT_VISITED' }
  | { type: 'GO_NEXT_POINT' }
  | { type: 'COMPLETE_ROUTE' }
  | { type: 'RESET_ROUTE' }

export type NavigationPoint = RoutePoint & {
  navigationIndex: number
}

export type RejectionReason =
  | 'missing_place_id'
  | 'missing_coordinates'
  | 'hidden_place'
  | 'route_ineligible'
  | 'service_category'

export type QualityGateResult = {
  validPoints: NavigationPoint[]
  rejected: { point: RoutePoint; reason: RejectionReason }[]
  counts: Record<RejectionReason, number>
  canStart: boolean
}

export const initialNavigationState: RouteNavigationState = {
  status: 'not_started',
  currentPointIndex: 0,
  visitedPointIds: [],
}
