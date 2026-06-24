import { formatDistance } from '../../features/route-navigation/model/geo'
import type { NavigationPoint, RouteNavigationState } from '../../features/route-navigation/model/types'
import type { LocationStatus } from '../../shared/location/types'
import { RouteProgress } from './RouteProgress'

type Props = {
  state: RouteNavigationState
  points: NavigationPoint[]
  canStart: boolean
  blockMessage: string | null
  distanceToCurrentMeters: number | null
  accuracyMeters: number | null
  locationStatus: LocationStatus
  locationStale: boolean
  onStart: () => void
  onVisited: () => void
  onNext: () => void
  onComplete: () => void
  onReset: () => void
  onRequestLocation: () => void
}

const pointTitle = (point: NavigationPoint | undefined): string =>
  point?.place_title ?? (point ? `Место #${point.place_id}` : 'Точка маршрута')

const navigationUrl = (point: NavigationPoint | undefined): string | null => {
  if (!point || typeof point.lat !== 'number' || typeof point.lng !== 'number') return null
  if (!Number.isFinite(point.lat) || !Number.isFinite(point.lng)) return null
  return `https://www.google.com/maps/dir/?api=1&destination=${point.lat},${point.lng}&travelmode=walking`
}

const gpsLabel = (status: LocationStatus, distance: number | null, accuracy: number | null, stale: boolean): string => {
  if (stale) return 'Позиция устарела. Обновите геопозицию перед оценкой расстояния.'
  if (accuracy !== null && accuracy > 100) return 'Точность геопозиции недостаточна. Отметьте точку вручную, когда окажетесь на месте.'
  const formattedDistance = formatDistance(distance)
  const formattedAccuracy = formatDistance(accuracy)
  if (formattedDistance) {
    return `До текущей точки: ${formattedDistance}${formattedAccuracy ? `, точность GPS около ${formattedAccuracy}` : ''}.`
  }
  if (status === 'requesting') return 'Запрашиваем геолокацию для расчета расстояния.'
  if (status === 'denied') return 'Геолокация запрещена. Можно идти по маршруту вручную.'
  if (status === 'unavailable' || status === 'insecure') return 'Геопозиция недоступна. Доступен ручной режим.'
  return 'Включите геолокацию, чтобы видеть расстояние до точки.'
}

export const RouteNavigationPanel = ({
  state,
  points,
  canStart,
  blockMessage,
  distanceToCurrentMeters,
  accuracyMeters,
  locationStatus,
  locationStale,
  onStart,
  onVisited,
  onNext,
  onComplete,
  onReset,
  onRequestLocation,
}: Props) => {
  const current = points[state.currentPointIndex]
  const currentNavigationUrl = navigationUrl(current)

  if (state.status === 'completed') {
    return (
      <section className="route-nav-panel completed" data-testid="route-completed-panel">
        <h2>Маршрут завершен</h2>
        <p>Посещено точек: {state.visitedPointIds.length} из {points.length}.</p>
        <button type="button" onClick={onReset}>Пройти заново</button>
      </section>
    )
  }

  if (state.status === 'active') {
    return (
      <section className="route-nav-panel active" data-testid="route-active-panel">
        <RouteProgress visitedCount={state.visitedPointIds.length} totalCount={points.length} />
        <p className="route-nav-step">Точка {state.currentPointIndex + 1} из {points.length}</p>
        <h2>{pointTitle(current)}</h2>
        <p>{[current?.category, current?.address].filter(Boolean).join(' · ') || 'Адрес уточняется'}</p>
        <p className="route-nav-gps" data-testid="route-gps-status">
          {gpsLabel(locationStatus, distanceToCurrentMeters, accuracyMeters, locationStale)}
        </p>
        <div className="route-nav-actions">
          <button type="button" onClick={onVisited}>Я на месте</button>
          <button type="button" onClick={onNext}>Следующая</button>
          <button type="button" className="muted" onClick={onRequestLocation}>Обновить GPS</button>
          {currentNavigationUrl ? (
            <a className="route-nav-button muted" href={currentNavigationUrl} target="_blank" rel="noreferrer">
              Открыть навигатор
            </a>
          ) : null}
          <button type="button" className="muted" onClick={onComplete}>Завершить</button>
        </div>
      </section>
    )
  }

  return (
    <section className="route-nav-panel" data-testid="route-preview-panel">
      <h2>Готовы пройти маршрут?</h2>
      {blockMessage ? (
        <p className="route-nav-warning">{blockMessage}</p>
      ) : (
        <p>Карта показывает маршрут, точки и ваше положение после разрешения геолокации. Без GPS доступен ручной режим.</p>
      )}
      <button type="button" disabled={!canStart} onClick={onStart}>Начать маршрут</button>
    </section>
  )
}
