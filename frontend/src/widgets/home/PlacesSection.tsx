import { Link } from 'react-router-dom'
import { PlaceCard } from '../../components/places/PlaceCard'
import { ErrorState } from '../../components/ui/ErrorState'
import { Skeleton } from '../../components/ui/Skeleton'
import type { Place } from '../../entities/place/model/types'

type PlacesSectionProps = {
  loading: boolean
  error: string | null
  places: Place[]
}

export const PlacesSection = ({ loading, error, places }: PlacesSectionProps) => {
  return (
    <section className="places-section">
      <div className="places-section-header">
        <div>
          <h2>Места</h2>
          <p className="places-muted">Быстрый срез по текущему городу</p>
        </div>
        <div className="places-section-meta">
          <span className="places-muted">
            {loading ? 'Загрузка' : `${places.length} найдено`}
          </span>
          <Link className="section-link" to="/places">
            Смотреть все места
          </Link>
        </div>
      </div>

      {error ? (
        <ErrorState title="Места не загрузились" description={error} />
      ) : null}

      {!error && loading ? (
        <div className="places-grid">
          {Array.from({ length: 6 }, (_, index) => <Skeleton key={index} />)}
        </div>
      ) : null}

      {!error && !loading ? (
        <div className="places-grid">
          {places.slice(0, 12).map((place) => (
            <PlaceCard key={place.id} place={place} />
          ))}
        </div>
      ) : null}
    </section>
  )
}
