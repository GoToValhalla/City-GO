import { useEffect, useState } from 'react'
import { getNearbyPlaces, type NearbyPlace } from '../../api/nearby/nearby.api'
import { AppHeader } from '../../components/ui/AppHeader'
import { PageBreadcrumbs } from '../../components/ui/PageBreadcrumbs'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { NearbyControls } from './NearbyControls'
import { NearbyResults } from './NearbyResults'

const FALLBACK_LAT = 54.9587
const FALLBACK_LNG = 20.475
const RADIUS_OPTIONS = [0.1, 0.3, 1]

export const NearbyPage = () => {
  const [places, setPlaces] = useState<NearbyPlace[]>([])
  const [radiusKm, setRadiusKm] = useState(0.3)
  const [lat, setLat] = useState(FALLBACK_LAT)
  const [lng, setLng] = useState(FALLBACK_LNG)
  const [locationLabel, setLocationLabel] = useState('Центр Зеленоградска')
  const [loading, setLoading] = useState(true)
  const [locating, setLocating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadPlaces = async () => {
      setLoading(true)
      try {
        setPlaces(await getNearbyPlaces(lat, lng, radiusKm))
        setError(null)
      } catch {
        setError('Не удалось загрузить места рядом')
      } finally {
        setLoading(false)
      }
    }
    loadPlaces()
  }, [lat, lng, radiusKm])

  const handleUseMyLocation = () => {
    if (!navigator.geolocation) return setError('Браузер не поддерживает геолокацию')
    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLat(Number(position.coords.latitude.toFixed(6)))
        setLng(Number(position.coords.longitude.toFixed(6)))
        setLocationLabel('Моя геолокация')
        setLocating(false)
      },
      () => { setError('Не удалось получить геолокацию'); setLocating(false) },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
    )
  }

  return (
    <div className="app-screen">
      <div className="app-container">
        <AppHeader />
        <PageBreadcrumbs items={[{ label: 'Главная', to: '/' }, { label: 'Рядом' }]}
          right={<div className="places-muted">{loading ? 'Загрузка' : `${places.length} рядом`}</div>} />
        <section className="places-list-panel">
          <SectionHeader title="Рядом с точкой"
            description="Ближайшие места с фото, адресом, временем визита и открытием. Можно сменить радиус или взять текущую геолокацию." />
          <NearbyControls lat={lat} lng={lng} locating={locating}
            locationLabel={locationLabel} radiusKm={radiusKm}
            radiusOptions={RADIUS_OPTIONS} onRadius={setRadiusKm}
            onUseLocation={handleUseMyLocation} />
        </section>
        <NearbyResults error={error} loading={loading} places={places} />
      </div>
    </div>
  )
}
