import { Link } from 'react-router-dom'
import { PlaceCard } from '../../components/places/PlaceCard'
import { EmptyState } from '../../components/ui/EmptyState'
import type { NearbyPlace } from '../../api/nearby/nearby.api'

type Props = {
  error: string | null
  loading: boolean
  places: NearbyPlace[]
}

export const NearbyResults = ({ error, loading, places }: Props) => {
  if (error) return <section className="state-panel state-panel-error">{error}</section>
  if (!loading && places.length === 0) return <EmptyState message="Рядом ничего не найдено." />
  return (
    <section className="places-grid places-page-section">
      {places.map((place) => (
        <div className="discovery-card-wrap" key={place.id}>
          <PlaceCard place={place} />
          <Link className="discovery-card-action" to={`/places/${place.slug}`}>
            {place.distance_km} км от точки
          </Link>
        </div>
      ))}
    </section>
  )
}
