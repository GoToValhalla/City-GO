import { useMemo } from 'react'
import type { NavigationPoint } from '../../features/route-navigation/model/types'
import { RoutePointMarkers } from './RoutePointMarkers'
import { RoutePolyline } from './RoutePolyline'
import { normalizePointsForMap } from './routeMapMath'

type Props = {
  points: NavigationPoint[]
  currentPointId?: number
  visitedPointIds: number[]
}

export const RouteMapPreview = ({ points, currentPointId, visitedPointIds }: Props) => {
  const mapPoints = useMemo(() => normalizePointsForMap(points), [points])

  if (mapPoints.length === 0) {
    return (
      <div className="route-nav-map empty" data-testid="route-map-empty">
        <strong>Схема маршрута недоступна</strong>
        <span>Для схемы нужны координаты точек.</span>
      </div>
    )
  }

  return (
    <section className="route-nav-map" aria-label="Схема маршрута" data-testid="route-map">
      <svg viewBox="0 0 100 100" role="img" aria-label="Точки и линия маршрута">
        <rect width="100" height="100" rx="4" className="route-nav-grid" />
        <RoutePolyline points={mapPoints} />
        <RoutePointMarkers
          points={mapPoints}
          currentPointId={currentPointId}
          visitedPointIds={visitedPointIds}
        />
      </svg>
      <p>{mapPoints.length} навигационных точек. Линия соединяет их прямыми отрезками.</p>
    </section>
  )
}
