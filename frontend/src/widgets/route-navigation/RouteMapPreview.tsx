import type { GeoPoint } from '../../features/route-navigation/model/geo'
import type { NavigationPoint } from '../../features/route-navigation/model/types'
import type { LocationStatus } from '../../shared/location/types'
import { MapLibreMap } from '../../shared/map/MapLibreMap'

type Props = {
  points: NavigationPoint[]
  currentPointId?: number
  visitedPointIds: number[]
  userLocation: GeoPoint | null
  locationStatus: LocationStatus
  locationError: string | null
  onRequestLocation: () => void
}

const valid = (point: NavigationPoint): boolean =>
  Number.isFinite(point.lat) && Number.isFinite(point.lng)

export const RouteMapPreview = ({
  currentPointId, locationError, locationStatus, onRequestLocation,
  points, userLocation, visitedPointIds,
}: Props) => {
  const mapPoints = points.filter(valid).map((point) => ({
    id: point.place_id,
    latitude: Number(point.lat),
    longitude: Number(point.lng),
    title: point.place_title ?? `Место #${point.place_id}`,
    category: point.category,
    order: point.navigationIndex + 1,
    visited: visitedPointIds.includes(point.place_id),
  }))
  if (!mapPoints.length) return <div className="route-nav-map empty" data-testid="route-map-empty">
    <strong>Карта маршрута недоступна</strong><span>Для карты нужны координаты точек.</span>
  </div>
  return <section className="route-nav-map" aria-label="Интерактивная карта маршрута" data-testid="route-map">
    <div className="route-nav-map-toolbar"><div><strong>Карта маршрута</strong>
      <span>{mapPoints.length} точек, интерактивная карта и ваше положение.</span></div>
      <button type="button" onClick={onRequestLocation}>
        {locationStatus === 'granted' ? 'Обновить позицию' : 'Я на карте'}
      </button>
    </div>
    <MapLibreMap points={mapPoints} activePointId={currentPointId} routeLine
      interactiveSelection={false} userLocation={userLocation ? {
        latitude: userLocation.lat, longitude: userLocation.lng,
        accuracy: userLocation.accuracy ?? null,
      } : null} />
    {locationError ? <p className="route-nav-location-status">{locationError}</p> : null}
  </section>
}
