import { AlertTriangle, Info } from 'lucide-react'
import type { RecommendationRouteResponse, RouteUserWarning } from '../../api/recommendations/recommendationRoute.types'

type Props = { route: RecommendationRouteResponse }

const fallbackWarnings = (warnings: string[]): RouteUserWarning[] => warnings.map((warning) => ({
  type: 'data_quality_low',
  severity: 'warning',
  user_message: warning,
  affected_place_ids: [],
  action_hint: 'Проверь детали мест перед прогулкой.',
}))

export const RouteWarnings = ({ route }: Props) => {
  const warnings = route.user_warnings?.length ? route.user_warnings : fallbackWarnings(route.warnings)
  if (!warnings.length) return null

  return (
    <div className="route-warning-stack">
      {warnings.map((warning) => {
        const Icon = warning.severity === 'warning' || warning.severity === 'error' ? AlertTriangle : Info
        return (
          <article className={`route-warning-card is-${warning.severity}`} key={`${warning.type}-${warning.user_message}`}>
            <strong><Icon size={18} /> {warning.user_message}</strong>
            {warning.action_hint ? <p>{warning.action_hint}</p> : null}
          </article>
        )
      })}
    </div>
  )
}
