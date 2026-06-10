import { useEffect, useState } from 'react'
import { getOpenNowPlaces, type OpenNowPlace } from '../../api/open-now/openNow.api'
import { AppHeader } from '../../components/ui/AppHeader'
import { PageBreadcrumbs } from '../../components/ui/PageBreadcrumbs'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { getCurrentCity, type CityOption } from '../../shared/city/currentCity'
import { OpenNowResults } from './OpenNowResults'

export const OpenNowPage = () => {
  const [city, setCity] = useState<CityOption>(getCurrentCity())
  const [places, setPlaces] = useState<OpenNowPlace[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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
        const data = await getOpenNowPlaces(city.slug)
        setPlaces(data)
      } catch (err) {
        console.error(err)
        setError('Не удалось загрузить open-now с backend')
      } finally {
        setLoading(false)
      }
    }

    loadPlaces()
  }, [city.slug])

  return (
    <div className="app-screen">
      <div className="app-container">
        <AppHeader />

        <PageBreadcrumbs
          items={[
            { label: 'Главная', to: '/' },
            { label: 'Открыто сейчас' },
          ]}
          right={
            <div style={{ color: '#64748b' }}>
              {loading ? 'Загрузка...' : `${places.length} открыто сейчас`}
            </div>
          }
        />

        <section className="places-list-panel">
          <SectionHeader
            title={`Открыто сейчас: ${city.name}`}
            description="Живой список мест из локального каталога: кафе, музеи, прогулки и вечерние точки, куда можно идти без долгого выбора."
          />
          <div className="discovery-stats">
            <span>{places.length} мест</span>
            <span>по расписанию каталога</span>
            <span>фото и детали в карточках</span>
          </div>
        </section>
        <OpenNowResults error={error} loading={loading} places={places} />
      </div>
    </div>
  )
}