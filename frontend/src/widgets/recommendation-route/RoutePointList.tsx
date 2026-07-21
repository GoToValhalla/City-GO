import { ArrowDown, ArrowUp, Clock, MapPin, Wand2, X } from 'lucide-react'
import type { RecommendationRoutePoint } from '../../api/recommendations/recommendationRoute.types'
import { openExternalUrl, twoGisMapLink, yandexMapLink } from '../../shared/map/externalMapLinks'
import { categoryLabel } from '../../shared/place/categoryLabels'
import { MAP_LINK_LABEL, UNCLEAR_ADDRESS_LABEL } from '../../shared/place/placeAddress'

type Props = {
  disabled?: boolean
  points: RecommendationRoutePoint[]
  reasons?: Record<string, string>
  activePlaceId?: string | null
  onMove?: (placeId: string, direction: 'up' | 'down') => void
  onRemove?: (placeId: string) => void
  onReplace?: (placeId: string) => void
}

const formatTime = (value?: string | null): string | null => {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

const validCoordinates = (point: RecommendationRoutePoint): { latitude: number; longitude: number } | null => {
  const latitude = Number(point.lat)
  const longitude = Number(point.lng)
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null
  if (Math.abs(latitude) > 90 || Math.abs(longitude) > 180 || (latitude === 0 && longitude === 0)) return null
  return { latitude, longitude }
}

const pointCategory = (point: RecommendationRoutePoint): string => {
  const raw = typeof point.category === 'string' ? point.category.trim() : ''
  return (raw ? categoryLabel(raw) : '') || 'Категория уточняется'
}

const pointTitle = (point: RecommendationRoutePoint, index: number): string =>
  point.title?.trim() || pointCategory(point) || `Точка ${index + 1}`

const locationText = (point: RecommendationRoutePoint): string => {
  if (point.has_address === false) return UNCLEAR_ADDRESS_LABEL
  const displayed = point.display_location?.trim() || point.address?.trim()
  if (displayed) return displayed
  const coordinates = validCoordinates(point)
  return coordinates ? `${coordinates.latitude.toFixed(4)}, ${coordinates.longitude.toFixed(4)}` : 'Местоположение уточняется'
}

const primaryMapUrl = (point: RecommendationRoutePoint): string | null =>
  point.navigation_url_yandex ?? point.navigation_url_google ?? point.navigation_url_osm ?? null

const criticalWarning = (point: RecommendationRoutePoint): string | null => {
  if (point.time_warning?.trim()) return point.time_warning
  if (point.has_address === false) return 'Адрес требует уточнения'
  if ((point.estimated_walk_minutes ?? 0) >= 25) return 'Длинный переход'
  return null
}

const visitText = (point: RecommendationRoutePoint): string => {
  const minutes = Number(point.visit_minutes)
  return Number.isFinite(minutes) && minutes > 0 ? `визит ${Math.round(minutes)} мин` : 'время визита уточняется'
}

export const RoutePointList = ({ disabled = false, points, reasons = {}, activePlaceId = null, onMove, onRemove, onReplace }: Props) => {
  if (points.length === 0) return <p className="route-muted" role="status">Точки не найдены</p>

  return <ol className="route-point-list route-point-list-compact">
    {points.map((point, index) => {
      const warning = criticalWarning(point)
      const isActive = activePlaceId === point.place_id
      const coordinates = validCoordinates(point)
      const arrivalTime = formatTime(point.estimated_arrival_time)
      return <li className={isActive ? 'is-active-route-point' : ''} key={`${point.place_id}-${index}`}>
        <span className="route-point-index">{index + 1}</span>
        <div className="route-point-main">
          <strong>{pointTitle(point, index)}</strong>
          <span>{pointCategory(point)}</span>
          {reasons[point.place_id]?.trim() ? <p className="route-point-reason">{reasons[point.place_id]}</p> : null}
        </div>
        <p className={point.has_address === false ? 'route-address-muted' : ''}>
          <MapPin size={15} /> {locationText(point)}
          {point.has_address === false && primaryMapUrl(point) ? <a className="route-map-link" href={primaryMapUrl(point) ?? '#'} target="_blank" rel="noopener noreferrer">{MAP_LINK_LABEL}</a> : null}
        </p>
        <p><Clock size={15} /> {arrivalTime ? `${arrivalTime} · ` : ''}{visitText(point)}</p>
        {warning ? <p className="route-warning-text">{warning}</p> : null}
        {coordinates ? <div className="tma-route-point-links">
          <button type="button" onClick={() => openExternalUrl(yandexMapLink(coordinates))}>Яндекс</button>
          <button type="button" onClick={() => openExternalUrl(twoGisMapLink(coordinates))}>2ГИС</button>
        </div> : null}
        <div className="route-point-actions">
          {onMove ? <><button type="button" disabled={disabled || index === 0} onClick={() => onMove(point.place_id, 'up')}><ArrowUp size={14} /> Выше</button><button type="button" disabled={disabled || index === points.length - 1} onClick={() => onMove(point.place_id, 'down')}><ArrowDown size={14} /> Ниже</button></> : null}
          {onReplace ? <button type="button" disabled={disabled} onClick={() => onReplace(point.place_id)}><Wand2 size={14} /> Заменить</button> : null}
          {onRemove ? <button type="button" disabled={disabled || points.length <= 1} onClick={() => onRemove(point.place_id)}><X size={14} /> Удалить</button> : null}
        </div>
      </li>
    })}
  </ol>
}
