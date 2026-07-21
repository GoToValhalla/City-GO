import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ErrorState } from '../../components/ui/ErrorState'
import { EmptyState } from '../../components/ui/EmptyState'
import { Skeleton } from '../../components/ui/Skeleton'
import { usePlacesPagination } from '../../features/places-list/usePlacesPagination'
import { PlacesLoadMoreTrigger } from '../../features/places-list/PlacesLoadMoreTrigger'
import { getCurrentCity } from '../../shared/city/currentCity'
import { categoryLabel } from '../../shared/place/categoryLabels'
import { TmaShell } from './TmaShell'

export const TmaPlacesPage = () => {
  const [city, setCity] = useState(getCurrentCity())
  const navigate = useNavigate()
  const { error, hasMore, loading, loadMore, places, retry } = usePlacesPagination(city.slug)
  const initialLoading = loading && places.length === 0
  const initialError = Boolean(error && places.length === 0)
  const incrementalError = Boolean(error && places.length > 0)

  useEffect(() => {
    const syncCity = () => setCity(getCurrentCity())
    window.addEventListener('citygo:city-changed', syncCity)
    return () => window.removeEventListener('citygo:city-changed', syncCity)
  }, [])

  return <TmaShell title={`Места: ${city.name}`}>
    {initialError ? <ErrorState title="Не удалось загрузить места" description={error ?? undefined} retryLabel="Повторить" onRetry={retry} /> : null}
    {initialLoading ? <div className="tma-place-card-list" role="status" aria-live="polite" aria-busy="true"><p>Загружаем места…</p><Skeleton /><Skeleton /><Skeleton /></div> : null}
    {!initialError && !initialLoading && places.length === 0 ? <EmptyState title="Мест пока нет" description="В этом городе ещё нет опубликованных мест." /> : null}
    {places.length > 0 ? (
      <div className="tma-place-card-list" aria-busy={loading}>
        {places.map((place) => (
          <button key={place.id} type="button" className="tma-place-card" onClick={() => navigate(`/telegram/places/${place.slug}`)}>
            {place.image_url ? <img src={place.image_url} alt="" loading="lazy" /> : <span className="telegram-map-pin" aria-hidden="true" />}
            <span className="tma-place-card-body">
              <strong>{place.title}</strong>
              <span>{categoryLabel(place.category)}{place.address ? ` · ${place.address}` : ''}</span>
            </span>
          </button>
        ))}
      </div>
    ) : null}
    {incrementalError ? <ErrorState title="Не удалось загрузить ещё места" description={error ?? undefined} retryLabel="Повторить" onRetry={retry} /> : null}
    {!error && places.length > 0 ? <PlacesLoadMoreTrigger onVisible={loadMore} loading={loading} hasMore={hasMore} /> : null}
  </TmaShell>
}
