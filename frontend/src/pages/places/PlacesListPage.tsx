import { Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { PlaceCard } from '../../components/places/PlaceCard'
import { AppHeader } from '../../components/ui/AppHeader'
import { filterPlaces } from '../../features/place-search/model/filterPlaces'
import { PlacesLoadMoreTrigger } from '../../features/places-list/PlacesLoadMoreTrigger'
import { usePlacesPagination } from '../../features/places-list/usePlacesPagination'
import { getCurrentCity, type CityOption } from '../../shared/city/currentCity'

export const PlacesListPage = () => {
  const [city, setCity] = useState<CityOption>(getCurrentCity())
  const [search, setSearch] = useState('')

  const { places, total, loading, hasMore, loadMore } = usePlacesPagination(city.slug)

  useEffect(() => {
    const syncCity = () => {
      setCity(getCurrentCity())
      setSearch('')
    }
    window.addEventListener('citygo:city-changed', syncCity)
    return () => window.removeEventListener('citygo:city-changed', syncCity)
  }, [])

  const filteredPlaces = useMemo(() => filterPlaces(places, search), [places, search])
  const isSearchActive = search.trim().length > 0
  const shownCount = isSearchActive ? filteredPlaces.length : places.length
  const effectiveTotal = isSearchActive ? filteredPlaces.length : total
  const isEmpty = !loading && filteredPlaces.length === 0

  return (
    <div className="app-screen">
      <div className="app-container">
        <AppHeader />

        <section className="places-list-panel">
          <div className="places-page-head">
            <div>
              <h1 className="places-list-title">Места: {city.name}</h1>
              <p className="places-muted">
                Поиск по текущей базе: кафе, музеи, парки, прогулки и вечерние места.
              </p>
              {!loading || places.length > 0 ? (
                <p className="places-muted">
                  {isSearchActive
                    ? `Найдено ${effectiveTotal} мест по текущему поиску.`
                    : `Показано ${shownCount} из ${effectiveTotal} мест.`}
                </p>
              ) : null}
            </div>
            <span className="place-chip">
              {loading && places.length === 0 ? 'загрузка' : `${effectiveTotal} мест`}
            </span>
          </div>

          <label className="places-search">
            <Search size={18} color="#6e6e73" />
            <input
              type="text"
              placeholder="Поиск мест, категорий и адресов..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
        </section>

        {isEmpty && (
          <section className="places-page-section">
            <div className="state-panel">
              По вашему запросу ничего не найдено.
            </div>
          </section>
        )}

        {!isEmpty && (
          <section className="places-grid places-page-section">
            {filteredPlaces.map((place) => (
              <PlaceCard key={place.id} place={place} />
            ))}
          </section>
        )}

        {!isSearchActive && (
          <PlacesLoadMoreTrigger onVisible={loadMore} loading={loading} hasMore={hasMore} />
        )}
      </div>
    </div>
  )
}
