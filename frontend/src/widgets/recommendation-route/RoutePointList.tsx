import { Clock, Footprints, MapPin, Navigation } from 'lucide-react'
import type { RecommendationRoutePoint } from '../../api/recommendations/recommendationRoute.types'
import { categoryLabel } from '../../shared/place/categoryLabels'
import { MAP_LINK_LABEL, UNCLEAR_ADDRESS_LABEL } from '../../shared/place/placeAddress'

type Props = {
  points: RecommendationRoutePoint[]
  reasons?: Record<string, string>
}

const rawPrefix = /^[\p{L}_ -]{2,32}:\s*/iu

const description = (point: RecommendationRoutePoint): string => {
  const cleaned = (point.short_description ?? '').replace(rawPrefix, '').trim()
  return cleaned && cleaned !== point.title ? cleaned : 'Точка выбрана из опубликованного каталога города.'
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

export const RoutePointList = ({ points, reasons = {} }: Props) => {
  if (points.length === 0) {
    return <p className="route-muted">Точки не найдены</p>
  }

  return (
    <ol className="route-point-list">
      {points.map((point, index) => {
        const score = point.scoring_breakdown?.interest ?? point.scoring_breakdown?.base_quality
        return (
        <li key={`${point.place_id}-${index}`}>
          <span className="route-point-index">{index}</span>
          {point.image_url ? (
            <img className="route-point-photo" src={point.image_url} alt={point.title ?? categoryLabel(point.category)} loading="lazy" />
          ) : (
            <div className="route-point-photo route-point-photo-fallback">
              <span>{categoryLabel(point.category)}</span>
            </div>
          )}
          <div className="route-point-main">
            <strong>{point.title ?? categoryLabel(point.category) ?? `Место ${point.place_id}`}</strong>
            <span>{categoryLabel(point.category) ?? point.category}</span>
            <p>{description(point)}</p>
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
          <div className="route-nav-links">
            {point.navigation_url_google && (
              <a href={point.navigation_url_google} target="_blank" rel="noopener noreferrer" className="route-nav-link">
                <Navigation size={13} /> Google Maps
              </a>
            )}
            {point.navigation_url_yandex && (
              <a href={point.navigation_url_yandex} target="_blank" rel="noopener noreferrer" className="route-nav-link">
                <Navigation size={13} /> Яндекс
              </a>
            )}
            {point.navigation_url_osm && (
              <a href={point.navigation_url_osm} target="_blank" rel="noopener noreferrer" className="route-nav-link">
                <Navigation size={13} /> OSM
              </a>
            )}
          </div>
          {formatTime(point.estimated_arrival_time) ? (
            <p><Clock size={15} /> {formatTime(point.estimated_arrival_time)}</p>
          ) : null}
          <p><Footprints size={15} /> визит {point.visit_minutes} мин</p>
          {typeof score === 'number' ? <p className="route-status-chip">Совпадение {Math.round(score * 100)}%</p> : null}
          {point.time_warning ? <p className="route-warning-text">{point.time_warning}</p> : null}
        </li>
        )
      })}
    </ol>
  )
}
