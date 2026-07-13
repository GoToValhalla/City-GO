import { useEffect, useMemo, useState } from 'react'
import { getPlacesByCityResponse } from '../../api/places/places.api'
import { AppHeader } from '../../components/ui/AppHeader'
import type { Place } from '../../entities/place/model/types'
import { getCurrentCity, type CityOption } from '../../shared/city/currentCity'
import { DiagnosticsPanel } from '../../shared/debug/DiagnosticsPanel'
import { HomeHero } from '../../widgets/home/HomeHero'
import { PlacesSection } from '../../widgets/home/PlacesSection'
import { QuickActions } from '../../widgets/home/QuickActions'

export const HomePage = () => {
  const [city, setCity] = useState<CityOption>(getCurrentCity())
  const [places, setPlaces] = useState<Place[]>([])
  const [placesTotal, setPlacesTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const syncCity = () => {
      setLoading(true)
      setError(null)
      setCity(getCurrentCity())
    }
    window.addEventListener('citygo:city-changed', syncCity)
    return () => window.removeEventListener('citygo:city-changed', syncCity)
  }, [])

  useEffect(() => {
    let active = true
    getPlacesByCityResponse(city.slug)
      .then((data) => {
        if (!active) return
        setPlaces(data.items)
        setPlacesTotal(data.total)
      })
      .catch((requestError) => {
        console.error(requestError)
        if (!active) return
        setError('Не удалось загрузить места')
        setPlaces([])
        setPlacesTotal(0)
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [city.slug])

  const categoriesCount = useMemo(() => new Set(places.map((place) => place.category).filter(Boolean)).size, [places])

  return <div className="app-screen"><div className="app-container">
    <AppHeader />
    <main className="home-shell">
      <HomeHero categoriesCount={categoriesCount} city={city} places={places} placesTotal={placesTotal} />
      <section className="home-section-heading"><div><p>Начните с настроения</p><h2>Что хочется сейчас?</h2></div></section>
      <QuickActions citySlug={city.slug} />
      <PlacesSection citySlug={city.slug} error={error} loading={loading} places={places} total={placesTotal} />
      <DiagnosticsPanel compact payload={{ screen: 'home', category: 'ui', severity: error ? 'error' : 'info', city_slug: city.slug, title: 'Home diagnostics', summary: error ?? `${placesTotal} places available`, response_summary: { places_total: placesTotal, loaded: places.length } }} />
    </main>
  </div></div>
}
