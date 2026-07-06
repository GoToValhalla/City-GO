import { useEffect, useMemo, useState } from 'react'
import { getPlacesByCityResponse } from '../../api/places/places.api'
import { AppHeader } from '../../components/ui/AppHeader'
import type { Place } from '../../entities/place/model/types'
import { filterPlaces } from '../../features/place-search/model/filterPlaces'
import { getCurrentCity, type CityOption } from '../../shared/city/currentCity'
import { DiagnosticsPanel } from '../../shared/debug/DiagnosticsPanel'
import { HomeHero } from '../../widgets/home/HomeHero'
import { HomeStats } from '../../widgets/home/HomeStats'
import { PlacesSection } from '../../widgets/home/PlacesSection'
import { QuickActions } from '../../widgets/home/QuickActions'

export const HomePage = () => {
  const [city, setCity] = useState<CityOption>(getCurrentCity())
  const [places, setPlaces] = useState<Place[]>([])
  const [placesTotal, setPlacesTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    const syncCity = () => {
      setCity(getCurrentCity())
    }

    window.addEventListener('citygo:city-changed', syncCity)

    return () => {
      window.removeEventListener('citygo:city-changed', syncCity)
    }
  }, [])

  useEffect(() => {
    const loadPlaces = async () => {
      try {
        setLoading(true)
        setError(null)

        const data = await getPlacesByCityResponse(city.slug)

        setPlaces(data.items)
        setPlacesTotal(data.total)
      } catch (err) {
        console.error(err)
        setError('Не удалось загрузить места')
        setPlaces([])
        setPlacesTotal(0)
      } finally {
        setLoading(false)
      }
    }

    loadPlaces()
  }, [city.slug])

  const filteredPlaces = useMemo(() => filterPlaces(places, search), [places, search])
  const statsPlacesCount = search ? filteredPlaces.length : placesTotal

  return (
    <div className="app-screen">
      <div className="app-container">
        <AppHeader />
        <main className="home-shell">
          <HomeHero search={search} cityName={city.name} onSearchChange={setSearch} />
          <QuickActions />
          <HomeStats loading={loading} placesCount={statsPlacesCount} />
          <PlacesSection loading={loading} error={error} places={filteredPlaces} />
          <DiagnosticsPanel compact payload={{ screen: 'home', category: 'ui', severity: error ? 'error' : 'info', city_slug: city.slug, title: 'Home diagnostics', summary: error ?? `${statsPlacesCount} places shown`, response_summary: { places_total: placesTotal, filtered: filteredPlaces.length } }} />
        </main>
      </div>
    </div>
  )
}
