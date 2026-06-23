import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getRouteBySlug } from '../../api/routes/routes.api'
import type { RouteDetail } from '../../api/routes/routes.api'
import { AppHeader } from '../../components/ui/AppHeader'
import { Badge } from '../../components/ui/Badge'
import { ErrorState } from '../../components/ui/ErrorState'
import { PageBreadcrumbs } from '../../components/ui/PageBreadcrumbs'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { Skeleton } from '../../components/ui/Skeleton'
import { getRouteModeLabel } from '../../features/routes/model/getRouteModeLabel'
import { RouteNavigationView } from '../../widgets/route-navigation/RouteNavigationView'
import './RouteDetailPage.css'

export const RouteDetailPage = () => {
  const { slug } = useParams<{ slug: string }>()
  const [route, setRoute] = useState<RouteDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    const loadRoute = async () => {
      if (!slug) {
        setError('Некорректный адрес маршрута')
        setLoading(false)
        return
      }

      try {
        setLoading(true)
        setError(null)
        setRoute(await getRouteBySlug(slug))
      } catch (err) {
        console.error(err)
        setError('Не удалось загрузить маршрут')
      } finally {
        setLoading(false)
      }
    }

    void loadRoute()
  }, [reloadKey, slug])

  return (
    <div className="app-screen">
      <div className="app-container">
        <AppHeader />

        <PageBreadcrumbs
          items={[
            { label: 'Главная', to: '/' },
            { label: 'Маршруты', to: '/routes' },
            { label: 'Детали' },
          ]}
        />

        <section className="places-list-panel">
          <SectionHeader
            eyebrow="Маршрут"
            title={loading ? 'Загрузка маршрута' : route?.title ?? 'Маршрут'}
            description={
              error ||
              route?.short_description ||
              'Порядок точек, длительность и управление прогулкой.'
            }
          />

          <div className="route-card__badges">
            <Badge variant="brand">{getRouteModeLabel(route?.route_mode)}</Badge>
            <Badge variant="neutral">{route?.duration_minutes ? `≈ ${route.duration_minutes} мин` : 'Время уточняется'}</Badge>
            <Badge variant="neutral">{route?.distance_km ? `≈ ${route.distance_km} км` : 'Дистанция уточняется'}</Badge>
            <Badge variant="neutral">{route ? `${route.points.length} точек` : 'Точки загружаются'}</Badge>
          </div>
        </section>

        {loading ? (
          <main className="route-card-list route-state">
            <Skeleton />
            <Skeleton />
          </main>
        ) : null}

        {error && !loading ? (
          <section className="route-state">
            <ErrorState
              title="Маршрут не загрузился"
              description={error}
              onRetry={() => setReloadKey((value) => value + 1)}
            />
          </section>
        ) : null}

        {!loading && !error && route ? <RouteNavigationView key={route.id} route={route} /> : null}
      </div>
    </div>
  )
}
