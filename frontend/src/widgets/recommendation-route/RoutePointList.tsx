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
  return new Date(value).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

const locationText = (point: RecommendationRoutePoint): string => {
  if (point.has_address === false) return UNCLEAR_ADDRESS_LABEL
  return point.display_location ?? point.address ?? `${point.lat.toFixed(4)}, ${point.lng.toFixed(4)}`
}

const primaryMapUrl = (point: RecommendationRoutePoint): string | null =>
  point.navigation_url_yandex ?? point.navigation_url_google ?? point.navigation_url_osm ?? null

const criticalWarning = (point: RecommendationRoutePoint): string | null => {
  if (point.time_warning) return point.time_warning
  if (point.has_address === false) return 'Адрес требует уточнения'
  if ((point.estimated_walk_minutes ?? 0) >= 25) return 'Длинный переход'
  return null
}

export const RoutePointList = ({
  disabled = false,
  points,
  reasons = {},
  activePlaceId = null,
  onMove,
  onRemove,
  onReplace,
}: Props) => {
  if (points.length === 0) {
    return <p className="route-muted">Точки не найдены</p>
  }

  return (
    <ol className="route-point-list route-point-list-compact">
      {points.map((point, index) => {
        const warning = criticalWarning(point)
        const isActive = activePlaceId === point.place_id
        return (
          <li className={isActive ? 'is-active-route-point' : ''} key={`${point.place_id}-${index}`}>
            <span className="route-point-index">{index + 1}</span>
            <div className="route-point-main">
              <strong>{point.title ?? categoryLabel(point.category) ?? `Место ${point.place_id}`}</strong>
              <span>{categoryLabel(point.category) ?? point.category}</span>
              {reasons[point.place_id] ? <p className="route-point-reason">{reasons[point.place_id]}</p> : null}
            </div>
            <p className={point.has_address === false ? 'route-address-muted' : ''}>
              <MapPin size={15} /> {locationText(point)}
              {point.has_address === false && primaryMapUrl(point) ? (
                <a className="route-map-link" href={primaryMapUrl(point) ?? '#'} target="_blank" rel="noopener noreferrer">
                  {MAP_LINK_LABEL}
                </a>
              ) : null}
            </p>
            <p><Clock size={15} /> {formatTime(point.estimated_arrival_time) ? `${formatTime(point.estimated_arrival_time)} · ` : ''}визит {point.visit_minutes} мин</p>
            {warning ? <p className="route-warning-text">{warning}</p> : null}
            {Number.isFinite(point.lat) && Number.isFinite(point.lng) ? (
              <div className="tma-route-point-links">
                <button type="button" onClick={() => openExternalUrl(yandexMapLink({ latitude: point.lat, longitude: point.lng }))}>Яндекс</button>
                <button type="button" onClick={() => openExternalUrl(twoGisMapLink({ latitude: point.lat, longitude: point.lng }))}>2ГИС</button>
              </div>
            ) : null}
            <div className="route-point-actions">
              {onMove ? (
                <>
                  <button type="button" disabled={disabled || index === 0} onClick={() => onMove(point.place_id, 'up')}><ArrowUp size={14} /> Выше</button>
                  <button type="button" disabled={disabled || index === points.length - 1} onClick={() => onMove(point.place_id, 'down')}><ArrowDown size={14} /> Ниже</button>
                </>
              ) : null}
              {onReplace ? <button type="button" disabled={disabled} onClick={() => onReplace(point.place_id)}><Wand2 size={14} /> Заменить</button> : null}
              {onRemove ? <button type="button" disabled={disabled || points.length <= 1} onClick={() => onRemove(point.place_id)}><X size={14} /> Удалить</button> : null}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
