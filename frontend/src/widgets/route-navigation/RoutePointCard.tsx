import { Link } from 'react-router-dom'
import type { NavigationPoint } from '../../features/route-navigation/model/types'

type Props = {
  point: NavigationPoint
  current: boolean
  visited: boolean
}

const title = (point: NavigationPoint): string => point.place_title ?? `Место #${point.place_id}`

export const RoutePointCard = ({ point, current, visited }: Props) => (
  <article
    className={`route-nav-point-card${current ? ' current' : ''}${visited ? ' visited' : ''}`}
    data-testid={`route-point-card-${point.place_id}`}
  >
    <span className="route-nav-point-index">{visited ? '✓' : point.navigationIndex + 1}</span>
    <div>
      <strong>{point.place_slug ? <Link to={`/places/${point.place_slug}`}>{title(point)}</Link> : title(point)}</strong>
      <p>{[point.category, point.address].filter(Boolean).join(' · ') || 'Детали точки уточняются'}</p>
    </div>
  </article>
)
