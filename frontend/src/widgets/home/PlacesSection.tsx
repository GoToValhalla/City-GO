import { Link } from 'react-router-dom'
import { PlaceCard } from '../../components/places/PlaceCard'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { Skeleton } from '../../components/ui/Skeleton'
import type { Place } from '../../entities/place/model/types'
import { cityCatalogPath } from '../../features/city-routing/cityPaths'

type Props = { citySlug: string; loading: boolean; error: string | null; places: Place[]; total: number }

const openCityPicker = () => window.dispatchEvent(new CustomEvent('citygo:open-city-picker'))

export const PlacesSection = ({ citySlug, error, loading, places, total }: Props) => (
  <section className="places-section home-places-section">
    <div className="places-section-header"><div><p className="home-section-eyebrow">Реальные данные CITY GO</p><h2>Места в городе</h2></div>
      <div className="places-section-meta"><span className="home-count-label">{total} мест</span><Link className="section-link" to={cityCatalogPath(citySlug)}>Смотреть все</Link></div>
    </div>
    {error ? <ErrorState title="Город временно не отвечает" description={error} /> : null}
    {!error && loading ? <div className="places-grid home-place-grid">{Array.from({ length: 4 }, (_, index) => <Skeleton key={index} />)}</div> : null}
    {!error && !loading && places.length ? <div className="places-grid home-place-grid">{places.slice(0, 4).map((place) => <PlaceCard key={place.id} place={place} />)}</div> : null}
    {!error && !loading && !places.length ? <EmptyState title="Места ещё готовятся" description="В этом городе пока нет опубликованных мест. Выберите другой город." actionLabel="Выбрать город" onAction={openCityPicker} /> : null}
  </section>
)
