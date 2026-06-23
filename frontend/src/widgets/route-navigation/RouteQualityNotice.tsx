import type { QualityGateResult, RejectionReason } from '../../features/route-navigation/model/types'

const LABELS: Record<RejectionReason, string> = {
  missing_place_id: 'нет идентификатора места',
  missing_coordinates: 'нет координат',
  hidden_place: 'скрытые места',
  route_ineligible: 'исключены из маршрутов',
  service_category: 'сервисные категории',
}

type Props = {
  result: QualityGateResult
}

export const invalidRouteMessage = 'Маршрут пока нельзя пройти: недостаточно проверенных точек.'

export const RouteQualityNotice = ({ result }: Props) => {
  const items = Object.entries(result.counts).filter(([, count]) => count > 0)
  if (result.canStart && items.length === 0) return null
  return (
    <section className="route-nav-quality" data-testid="route-quality-notice">
      {!result.canStart ? <strong>{invalidRouteMessage}</strong> : <strong>Некоторые точки скрыты из навигации из-за качества данных.</strong>}
      {items.length > 0 ? (
        <ul>
          {items.map(([reason, count]) => (
            <li key={reason}>{LABELS[reason as RejectionReason]}: {count}</li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
