import { Link } from 'react-router-dom'
import { PlaceCard } from '../../components/places/PlaceCard'
import { EmptyState } from '../../components/ui/EmptyState'
import type { OpenNowPlace } from '../../api/open-now/openNow.api'

type Props = {
  error: string | null
  loading: boolean
  places: OpenNowPlace[]
}

export const OpenNowResults = ({ error, loading, places }: Props) => {
  if (error) return <section className="state-panel state-panel-error">{error}</section>
  if (!loading && places.length === 0) {
    return <EmptyState message="Сейчас нет мест, которые отмечены как открытые." />
  }
  return (
    <section className="places-grid places-page-section">
      {places.map((place) => (
        <div className="discovery-card-wrap" key={place.id}>
          <PlaceCard place={place} />
          <Link className="discovery-card-action" to={`/places/${place.slug}`}>
            Открыто до {place.close_time}
          </Link>
        </div>
      ))}
    </section>
  )
}
