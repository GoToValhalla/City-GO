import type { RecommendationRouteResponse } from '../../api/recommendations/recommendationRoute.types'
import { categoryLabel } from '../../shared/place/categoryLabels'

type Props = { route: RecommendationRouteResponse }

const minutes = (value: number | undefined): string => `${Math.round(value ?? 0)} мин`

export const RouteInsights = ({ route }: Props) => {
  const breakdown = route.time_breakdown ?? {}
  const distribution = Object.entries(route.category_distribution ?? {})
  const photoPoint = route.points.find((point) => point.image_url)

  return (
    <div className="route-insights">
      {photoPoint?.image_url ? <img className="route-insight-photo" src={photoPoint.image_url} alt={photoPoint.title ?? ''} /> : null}
      <div>
        <span>В пути</span>
        <strong>{minutes(breakdown.walk_time_minutes)}</strong>
      </div>
      <div>
        <span>На местах</span>
        <strong>{minutes(breakdown.visit_time_minutes)}</strong>
      </div>
      <div>
        <span>Пешком</span>
        <strong>{Math.round((route.total_walk_distance_meters ?? 0) / 100) / 10} км</strong>
      </div>
      <div>
        <span>Бюджет</span>
        <strong>{Math.round((breakdown.budget_utilization ?? 0) * 100)}%</strong>
      </div>
      {distribution.length ? (
        <div className="route-category-strip">
          {distribution.map(([category, count]) => (
            <span key={category}>{categoryLabel(category) ?? category}: {count}</span>
          ))}
        </div>
      ) : null}
    </div>
  )
}
