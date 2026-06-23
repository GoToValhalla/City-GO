import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getRouteBySlug } from '../../api/routes/routes.api'
import type { RouteDetail } from '../../api/routes/routes.api'
import { AppHeader } from '../../components/ui/AppHeader'
import { Badge } from '../../components/ui/Badge'
import { PageBreadcrumbs } from '../../components/ui/PageBreadcrumbs'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { SurfaceCard } from '../../components/ui/SurfaceCard'
import { getRouteModeLabel } from '../../features/routes/model/getRouteModeLabel'
import { RouteNavigationView } from '../../widgets/route-navigation/RouteNavigationView'
import './RouteDetailPage.css'

export const RouteDetailPage = () => {
  // Забираем slug маршрута из URL.
  const { slug } = useParams<{ slug: string }>()

  // Данные одного маршрута.
  const [route, setRoute] = useState<RouteDetail | null>(null)

  // Флаг загрузки detail-страницы.
  const [loading, setLoading] = useState(true)

  // Текст ошибки, если маршрут не удалось загрузить.
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadRoute = async () => {
      // Если slug отсутствует, сразу показываем ошибку.
      if (!slug) {
        setError('Некорректный slug маршрута')
        setLoading(false)
        return
      }

      try {
        // Перед новым запросом включаем loading и очищаем старую ошибку.
        setLoading(true)
        setError(null)

        // Загружаем маршрут с backend по slug.
        const data = await getRouteBySlug(slug)
        setRoute(data)
      } catch (err) {
        console.error(err)
        setError('Не удалось загрузить маршрут с backend')
      } finally {
        setLoading(false)
      }
    }

    loadRoute()
  }, [slug])

  return (
    <div className="app-screen">
      <div className="app-container">
        <AppHeader />

        <PageBreadcrumbs
          items={[
            { label: 'Home', to: '/' },
            { label: 'Routes', to: '/routes' },
            { label: 'Detail' },
          ]}
        />

        <section className="places-list-panel">
          <SectionHeader
            eyebrow="Route detail"
            title={loading ? 'Загрузка маршрута...' : route?.title ?? 'Маршрут'}
            description={
              error ||
              route?.short_description ||
              'Детальная страница маршрута по городу.'
            }
          />

          <div
            style={{
              marginTop: '18px',
              display: 'flex',
              gap: '10px',
              flexWrap: 'wrap',
            }}
          >
            <Badge variant="brand">Route</Badge>

            <Badge variant="neutral">
              {getRouteModeLabel(route?.route_mode)}
            </Badge>

            <Badge variant="neutral">
              {route?.duration_minutes ? `≈ ${route.duration_minutes} мин` : 'Без времени'}
            </Badge>

            <Badge variant="neutral">
              {route?.distance_km ? `≈ ${route.distance_km} км` : 'Без дистанции'}
            </Badge>

            <Badge variant="neutral">
              {route ? `${route.points.length} точки` : '...'}
            </Badge>
          </div>
        </section>

        {loading && (
          <section style={{ marginTop: '18px' }}>
            <SurfaceCard style={{ padding: '20px' }}>
              <p style={{ margin: 0, color: '#64748b' }}>Загрузка маршрута...</p>
            </SurfaceCard>
          </section>
        )}

        {error && !loading && (
          <section style={{ marginTop: '18px' }}>
            <SurfaceCard style={{ padding: '20px' }}>
              <p style={{ margin: 0, color: '#b91c1c' }}>{error}</p>
            </SurfaceCard>
          </section>
        )}

        {!loading && !error && route && <RouteNavigationView key={route.id} route={route} />}
      </div>
    </div>
  )
}
