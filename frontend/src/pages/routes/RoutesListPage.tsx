import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getRoutesByCity } from '../../api/routes/routes.api'
import type { Route } from '../../api/routes/routes.api'
import { AppHeader } from '../../components/ui/AppHeader'
import { Badge } from '../../components/ui/Badge'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { PageBreadcrumbs } from '../../components/ui/PageBreadcrumbs'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { Skeleton } from '../../components/ui/Skeleton'
import { getRouteModeLabel } from '../../features/routes/model/getRouteModeLabel'
import { getCurrentCity, type CityOption } from '../../shared/city/currentCity'

type RouteFilterMode = 'all' | 'walk' | 'public_transport' | 'mixed'

const filterOptions: Array<{ value: RouteFilterMode; label: string }> = [
  { value: 'all', label: 'Все' },
  { value: 'walk', label: 'Пешком' },
  { value: 'public_transport', label: 'Транспорт' },
  { value: 'mixed', label: 'Смешанные' },
]

export const RoutesListPage = () => {
  const navigate = useNavigate()
  const [city, setCity] = useState<CityOption>(getCurrentCity())
  const [routes, setRoutes] = useState<Route[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterMode, setFilterMode] = useState<RouteFilterMode>('all')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    const syncCity = () => {
      setCity(getCurrentCity())
      setFilterMode('all')
    }
    window.addEventListener('citygo:city-changed', syncCity)
    return () => window.removeEventListener('citygo:city-changed', syncCity)
  }, [])

  useEffect(() => {
    const loadRoutes = async () => {
      try {
        setLoading(true)
        setError(null)
        setRoutes(await getRoutesByCity(city.slug))
      } catch (err) {
        console.error(err)
        setError('Не удалось загрузить маршруты')
        setRoutes([])
      } finally {
        setLoading(false)
      }
    }

    void loadRoutes()
  }, [city.slug, reloadKey])

  const filteredRoutes = useMemo(() => {
    if (filterMode === 'all') return routes
    return routes.filter((route) => route.route_mode === filterMode)
  }, [routes, filterMode])

  return (
    <div className="app-screen">
      <div className="app-container">
        <AppHeader />

        <PageBreadcrumbs
          items={[
            { label: 'Главная', to: '/' },
            { label: 'Маршруты' },
          ]}
        />

        <section className="places-list-panel">
          <SectionHeader
            eyebrow={`Маршруты · ${city.name}`}
            title="Готовые прогулки"
            description="Выбирай сценарий, смотри точки по порядку и запускай прогулку без лишних настроек."
          />

          <div className="route-filter-row" role="list" aria-label="Фильтр маршрутов">
            {filterOptions.map((option) => (
              <button
                key={option.value}
                className={filterMode === option.value ? 'filter-chip is-active' : 'filter-chip'}
                type="button"
                onClick={() => setFilterMode(option.value)}
                aria-pressed={filterMode === option.value}
              >
                {option.label}
              </button>
            ))}
          </div>
        </section>

        {loading ? (
          <section className="route-card-list route-state">
            {Array.from({ length: 3 }, (_, index) => <Skeleton key={index} />)}
          </section>
        ) : null}

        {error && !loading ? (
          <section className="route-state">
            <ErrorState title="Маршруты не загрузились" description={error} onRetry={() => setReloadKey((value) => value + 1)} />
          </section>
        ) : null}

        {!loading && !error && filteredRoutes.length ? (
          <section className="route-card-list route-state">
            {filteredRoutes.map((route) => (
              <article className="route-card" key={route.id}>
                <div className="route-card__head">
                  <div>
                    <h3 className="route-card__title">{route.title}</h3>
                    {route.short_description ? (
                      <p className="route-card__description cg-clamp-2">{route.short_description}</p>
                    ) : null}
                  </div>
                  <Badge variant="brand">{getRouteModeLabel(route.route_mode)}</Badge>
                </div>

                <div className="route-card__badges">
                  <Badge variant="neutral">{route.duration_minutes ? `≈ ${route.duration_minutes} мин` : 'Время уточняется'}</Badge>
                  <Badge variant="neutral">{route.distance_km ? `≈ ${route.distance_km} км` : 'Дистанция уточняется'}</Badge>
                </div>

                <div className="route-card__footer">
                  <Link className="route-link" to={`/routes/${route.slug}`}>Открыть маршрут</Link>
                </div>
              </article>
            ))}
          </section>
        ) : null}

        {!loading && !error && !filteredRoutes.length ? (
          <section className="route-state">
            <EmptyState
              title="Маршруты не найдены"
              description="Попробуйте другой фильтр или соберите маршрут под себя."
              actionLabel="Собрать маршрут"
              onAction={() => navigate('/routes/generate')}
            />
          </section>
        ) : null}
      </div>
    </div>
  )
}
