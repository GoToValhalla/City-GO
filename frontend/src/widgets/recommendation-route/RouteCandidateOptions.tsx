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
  return typeof value === 'number' ? Math.round(value * 100) : null
}

export const RouteCandidateOptions = ({ disabled = false, options = [], onAdd }: Props) => {
  if (options.length === 0) return null
  const displayed = options.slice(0, MAX_VISIBLE_OPTIONS)

  return (
    <details className="route-result-tile route-candidate-details">
      <summary>
        <span>Добавить место</span>
        <small>{displayed.length} из {options.length}</small>
      </summary>
      <p className="route-muted">Короткий список подходящих точек, которые можно добавить в текущий маршрут.</p>
      <div className="route-candidate-grid">
        {displayed.map((point) => (
          <article className="route-candidate-card" key={point.place_id}>
            {point.image_url ? (
              <img className="route-candidate-photo" src={point.image_url} alt={point.title ?? categoryLabel(point.category)} loading="lazy" />
            ) : (
              <div className="route-candidate-photo route-point-photo-fallback">
                <span>{categoryLabel(point.category)}</span>
              </div>
            )}
            <div className="route-candidate-body">
              <span className="place-chip">{categoryLabel(point.category)}</span>
              <h3>{point.title ?? `Место ${point.place_id}`}</h3>
              <p>{point.short_description || point.address || `${point.lat.toFixed(4)}, ${point.lng.toFixed(4)}`}</p>
              <div className="route-candidate-meta">
                <span><MapPin size={14} /> {point.address ?? `${point.lat.toFixed(4)}, ${point.lng.toFixed(4)}`}</span>
                <span><Clock size={14} /> {point.visit_minutes} мин</span>
                {score(point) !== null ? <span>Совпадение {score(point)}%</span> : null}
              </div>
              <button type="button" className="route-candidate-action" disabled={disabled} onClick={() => onAdd(point.place_id)}>
                <Plus size={15} /> Добавить
              </button>
            </div>
          </article>
        ))}
      </div>
    </details>
  )
}
