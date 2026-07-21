import { Clock, MapPin, Plus } from 'lucide-react'
import type { RecommendationRoutePoint } from '../../api/recommendations/recommendationRoute.types'
import { categoryLabel } from '../../shared/place/categoryLabels'

type Props = {
  disabled?: boolean
  options?: RecommendationRoutePoint[]
  onAdd: (placeId: string) => void
}

const MAX_VISIBLE_OPTIONS = 6

const score = (point: RecommendationRoutePoint): number | null => {
  const value = point.scoring_breakdown?.interest ?? point.scoring_breakdown?.base_quality
  return typeof value === 'number' && Number.isFinite(value) ? Math.round(value * 100) : null
}

const knownCategoryText = (point: RecommendationRoutePoint): string => {
  const raw = typeof point.category === 'string' ? point.category.trim() : ''
  return raw ? categoryLabel(raw) : ''
}

const categoryText = (point: RecommendationRoutePoint): string => knownCategoryText(point) || 'Категория уточняется'

// Only reuse the category as a title fallback when it is a real, known
// category -- never the "уточняется" placeholder itself, which would
// otherwise render the same text twice (as the title and as the category).
const titleText = (point: RecommendationRoutePoint): string => point.title?.trim() || knownCategoryText(point) || 'Место без названия'

const coordinatesText = (point: RecommendationRoutePoint): string | null => {
  const latitude = Number(point.lat)
  const longitude = Number(point.lng)
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null
  if (Math.abs(latitude) > 90 || Math.abs(longitude) > 180 || (latitude === 0 && longitude === 0)) return null
  return `${latitude.toFixed(4)}, ${longitude.toFixed(4)}`
}

const locationText = (point: RecommendationRoutePoint): string => point.address?.trim() || point.display_location?.trim() || coordinatesText(point) || 'Местоположение уточняется'

const visitText = (point: RecommendationRoutePoint): string => {
  const minutes = Number(point.visit_minutes)
  return Number.isFinite(minutes) && minutes > 0 ? `${Math.round(minutes)} мин` : 'время уточняется'
}

export const RouteCandidateOptions = ({ disabled = false, options = [], onAdd }: Props) => {
  if (options.length === 0) return null
  const displayed = options.slice(0, MAX_VISIBLE_OPTIONS)

  return <details className="route-result-tile route-candidate-details">
    <summary><span>Добавить место</span><small>{displayed.length} из {options.length}</small></summary>
    <p className="route-muted">Короткий список подходящих точек, которые можно добавить в текущий маршрут.</p>
    <div className="route-candidate-grid">
      {displayed.map((point) => {
        const category = categoryText(point)
        const title = titleText(point)
        const location = locationText(point)
        const matchScore = score(point)
        return <article className="route-candidate-card" key={point.place_id}>
          {point.image_url?.trim() ? <img className="route-candidate-photo" src={point.image_url} alt={title} loading="lazy" /> : (
            // The place-chip below is the single source of the category
            // text; this placeholder tile must not repeat it verbatim.
            <div className="route-candidate-photo route-point-photo-fallback" role="img" aria-label={`Фото недоступно: ${category}`} />
          )}
          <div className="route-candidate-body">
            <span className="place-chip">{category}</span>
            <h3>{title}</h3>
            <p>{point.short_description?.trim() || location}</p>
            <div className="route-candidate-meta">
              <span><MapPin size={14} /> {location}</span>
              <span><Clock size={14} /> {visitText(point)}</span>
              {matchScore !== null ? <span>Совпадение {matchScore}%</span> : null}
            </div>
            <button type="button" className="route-candidate-action" disabled={disabled} onClick={() => onAdd(point.place_id)}><Plus size={15} /> Добавить</button>
          </div>
        </article>
      })}
    </div>
  </details>
}
