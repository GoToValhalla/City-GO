import { SlidersHorizontal } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Button } from '../../components/ui/Button'
import { AppHeader } from '../../components/ui/AppHeader'
import { FilterChips, FilterSheet, PlaceList, PlaceMapPanel, SearchBar } from '../../components/places'
import type { FilterChipOption } from '../../components/places/FilterChips'
import type { FilterSheetDraft } from '../../components/places/FilterSheet'
import { ALL_VALUE } from '../../components/places/placeFilterConstants'
import { placeStatus } from '../../components/places/placeViewModel'
import { filterPlaces } from '../../features/place-search/model/filterPlaces'
import { PlacesLoadMoreTrigger } from '../../features/places-list/PlacesLoadMoreTrigger'
import { usePlacesPagination } from '../../features/places-list/usePlacesPagination'
import { getCurrentCity, type CityOption } from '../../shared/city/currentCity'
import { useUserLocation } from '../../shared/location/useUserLocation'
import { categoryLabel } from '../../shared/place/categoryLabels'

const initialFilters: FilterSheetDraft = {
  category: ALL_VALUE,
  onlyOpen: false,
  radiusKm: null,
  minRating: null,
}

export const PlacesListPage = () => {
  const [city, setCity] = useState<CityOption>(getCurrentCity())
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState<FilterSheetDraft>(initialFilters)
  const [draftFilters, setDraftFilters] = useState<FilterSheetDraft>(initialFilters)
  const [filterSheetOpen, setFilterSheetOpen] = useState(false)
  const [activePlaceId, setActivePlaceId] = useState<number | null>(null)
  const userLocation = useUserLocation()

  const { places, total, loading, error, hasMore, loadMore, retry } = usePlacesPagination(city.slug)

  useEffect(() => {
    const syncCity = () => {
      setCity(getCurrentCity())
      setSearch('')
      setFilters(initialFilters)
      setDraftFilters(initialFilters)
      setActivePlaceId(null)
      setFilterSheetOpen(false)
    }
    window.addEventListener('citygo:city-changed', syncCity)
    return () => window.removeEventListener('citygo:city-changed', syncCity)
  }, [])

  const categoryOptions = useMemo<FilterChipOption[]>(() => {
    const counters = places.reduce<Record<string, number>>((acc, place) => {
      acc[place.category] = (acc[place.category] ?? 0) + 1
      return acc
    }, {})

    return Object.entries(counters)
      .sort(([, leftCount], [, rightCount]) => rightCount - leftCount)
      .map(([value, count]) => ({ value, label: categoryLabel(value), count }))
  }, [places])

  const filteredPlaces = useMemo(() => {
    const bySearch = filterPlaces(places, search)
    return bySearch.filter((place) => {
      if (filters.category !== ALL_VALUE && place.category !== filters.category) return false
      if (filters.onlyOpen && placeStatus(place) !== 'open') return false
      return true
    })
  }, [filters.category, filters.onlyOpen, places, search])

  useEffect(() => {
    if (filteredPlaces.length === 0) {
      setActivePlaceId(null)
      return
    }
    if (!activePlaceId || !filteredPlaces.some((place) => place.id === activePlaceId)) {
      setActivePlaceId(filteredPlaces[0].id)
    }
  }, [activePlaceId, filteredPlaces])

  const isSearchActive = search.trim().length > 0
  const shownCount = isSearchActive || filters.category !== ALL_VALUE || filters.onlyOpen ? filteredPlaces.length : places.length
  const effectiveTotal = isSearchActive || filters.category !== ALL_VALUE || filters.onlyOpen ? filteredPlaces.length : total
  const loadingMore = loading && places.length > 0

  const resetFilters = () => {
    setSearch('')
    setFilters(initialFilters)
    setDraftFilters(initialFilters)
    setActivePlaceId(null)
    setFilterSheetOpen(false)
  }

  const applyFilters = () => {
    setFilters(draftFilters)
    setFilterSheetOpen(false)
  }

  const handleChipChange = (category: string) => {
    const nextFilters = { ...filters, category }
    setFilters(nextFilters)
    setDraftFilters(nextFilters)
  }

  return (
    <div className="app-screen">
      <div className="app-container">
        <AppHeader />

        <section className="places-list-panel">
          <div className="places-page-head">
            <div>
              <h1 className="places-list-title">Места: {city.name}</h1>
              <p className="places-muted">
                Карта и карточки мест с фото, статусом, категорией и быстрым переходом к деталям.
              </p>
              {!loading || places.length > 0 ? (
                <p className="places-muted">
                  {isSearchActive || filters.category !== ALL_VALUE || filters.onlyOpen
                    ? `Найдено ${effectiveTotal} мест.`
                    : `Показано ${shownCount} из ${effectiveTotal} мест.`}
                </p>
              ) : null}
            </div>
            <Button variant="ghost" size="md" leftIcon={<SlidersHorizontal size={17} />} onClick={() => setFilterSheetOpen(true)}>
              Фильтры
            </Button>
          </div>

          <SearchBar
            value={search}
            onChange={setSearch}
            placeholder="Поиск мест в городе"
            loading={loading && places.length === 0}
          />

          <FilterChips options={categoryOptions} value={filters.category} onChange={handleChipChange} />
        </section>

        <section className="places-map-list-layout">
          <PlaceMapPanel
            places={filteredPlaces}
            activePlaceId={activePlaceId}
            userLocation={userLocation.coordinates}
            locationLoading={userLocation.status === 'loading'}
            locationError={userLocation.error}
            onActivePlaceChange={setActivePlaceId}
            onRequestLocation={userLocation.requestLocation}
          />

          <PlaceList
            places={filteredPlaces}
            loading={loading && places.length === 0}
            loadingMore={loadingMore}
            error={error}
            activePlaceId={activePlaceId}
            onActivePlaceChange={setActivePlaceId}
            onRetry={retry}
            onResetFilters={resetFilters}
          />
        </section>

        {!isSearchActive && filters.category === ALL_VALUE && !filters.onlyOpen ? (
          <PlacesLoadMoreTrigger onVisible={loadMore} loading={loading} hasMore={hasMore} />
        ) : null}

        <FilterSheet
          open={filterSheetOpen}
          value={draftFilters}
          categories={categoryOptions}
          onChange={setDraftFilters}
          onApply={applyFilters}
          onReset={resetFilters}
          onClose={() => setFilterSheetOpen(false)}
        />
      </div>
    </div>
  )
}