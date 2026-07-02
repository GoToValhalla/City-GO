import { AlertTriangle, Info } from 'lucide-react'
import type { RecommendationRouteResponse, RouteUserWarning } from '../../api/recommendations/recommendationRoute.types'

type Props = { route: RecommendationRouteResponse }

const isTechnicalCode = (value: string): boolean => /^[a-z0-9_]+$/.test(value.trim())

const cleanMessage = (value: string): string => {
  if (!isTechnicalCode(value)) return value
  if (value.includes('photo')) return 'У части мест пока нет фото.'
  if (value.includes('budget')) return 'Маршрут немного выходит за выбранное время.'
  if (value.includes('walk') || value.includes('transfer')) return 'В маршруте есть длинные переходы пешком.'
  if (value.includes('interest')) return 'Маршрут собран без точного совпадения по интересам.'
  if (value.includes('neutral')) return 'Добавлены нейтральные точки, чтобы маршрут был полезнее.'
  if (value.includes('short') || value.includes('density') || value.includes('insufficient')) return 'Маршрут пока короткий из-за качества доступных данных.'
  return 'Маршрут собран с ограничениями по данным.'
}

const fallbackWarnings = (warnings: string[]): RouteUserWarning[] => warnings.map((warning) => ({
  type: warning,
  severity: 'warning',
  user_message: cleanMessage(warning),
  affected_place_ids: [],
  action_hint: 'Проверь детали мест перед прогулкой.',
}))

const normalizeWarning = (warning: RouteUserWarning): RouteUserWarning => ({
  ...warning,
  type: isTechnicalCode(warning.type) ? 'data_note' : warning.type,
  user_message: cleanMessage(warning.user_message),
  action_hint: warning.action_hint && isTechnicalCode(warning.action_hint) ? 'Проверь детали мест перед прогулкой.' : warning.action_hint,
})

const uniqueWarnings = (warnings: RouteUserWarning[]): RouteUserWarning[] => {
  const seen = new Set<string>()
  return warnings.filter((warning) => {
    const key = `${warning.severity}:${warning.user_message}:${warning.action_hint ?? ''}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

export const RouteWarnings = ({ route }: Props) => {
  const source = route.user_warnings?.length ? route.user_warnings : fallbackWarnings(route.warnings)
  const warnings = uniqueWarnings(source.map(normalizeWarning)).slice(0, 5)
  if (!warnings.length) return null

  return (
    <details className="route-warning-details">
      <summary>
        <AlertTriangle size={18} />
        <span>Есть нюансы данных</span>
        <small>{warnings.length}</small>
      </summary>
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
    </details>
  )
}
