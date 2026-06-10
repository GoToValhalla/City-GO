import type { RecommendationRouteResponse } from '../../../api/recommendations/recommendationRoute.types'

export const routeMatchesCity = (route: RecommendationRouteResponse, citySlug: string): boolean => {
  return route.points.every((point) => !point.city_slug || point.city_slug === citySlug)
}
