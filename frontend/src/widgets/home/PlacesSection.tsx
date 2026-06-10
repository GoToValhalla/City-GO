import { PlaceCard } from '../../components/places/PlaceCard'
import type { Place } from '../../entities/place/model/types'
import { Link } from 'react-router-dom'

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
          <p className="places-muted">Быстрый срез по текущей базе Зеленоградска</p>
        </div>
        <div className="places-section-meta">
          <span className="places-muted">
            {loading ? 'Загрузка...' : `${places.length} найдено`}
          </span>
          <Link className="section-link" to="/places">
            Смотреть все места
          </Link>
        </div>
      </div>

      {error && (
        <div className="state-panel state-panel-error">
          {error}
        </div>
      )}

      {!error && (
        <div className="places-grid">
          {places.slice(0, 12).map((place) => (
            <PlaceCard key={place.id} place={place} />
          ))}
        </div>
      )}
    </section>
  )
}
