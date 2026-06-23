import type { NavigationPoint, RouteNavigationState } from '../../features/route-navigation/model/types'
import { RouteProgress } from './RouteProgress'

type Props = {
  state: RouteNavigationState
  points: NavigationPoint[]
  canStart: boolean
  blockMessage: string | null
  onStart: () => void
  onVisited: () => void
  onNext: () => void
  onComplete: () => void
  onReset: () => void
}

const pointTitle = (point: NavigationPoint | undefined): string =>
  point?.place_title ?? (point ? `Место #${point.place_id}` : 'Точка маршрута')

export const RouteNavigationPanel = ({
  state, points, canStart, blockMessage, onStart, onVisited, onNext, onComplete, onReset,
}: Props) => {
  const current = points[state.currentPointIndex]
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
        <div className="route-nav-actions">
          <button type="button" onClick={onVisited}>Я на месте</button>
          <button type="button" onClick={onNext}>Следующая</button>
          <button type="button" className="muted" onClick={onComplete}>Завершить</button>
        </div>
      </section>
    )
  }

  return (
    <section className="route-nav-panel" data-testid="route-preview-panel">
      <h2>Готовы пройти маршрут?</h2>
      {blockMessage ? <p className="route-nav-warning">{blockMessage}</p> : <p>Навигация работает без GPS: отмечайте точки вручную.</p>}
      <button type="button" disabled={!canStart} onClick={onStart}>Начать маршрут</button>
    </section>
  )
}
