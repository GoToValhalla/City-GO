import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { getRoutesByCity } from '../../api/routes/routes.api'
import type { Route } from '../../api/routes/routes.api'
import { AppHeader } from '../../components/ui/AppHeader'
import { Badge } from '../../components/ui/Badge'
import { PageBreadcrumbs } from '../../components/ui/PageBreadcrumbs'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { SurfaceCard } from '../../components/ui/SurfaceCard'
import { getRouteModeLabel } from '../../features/routes/model/getRouteModeLabel'

// Режимы фильтрации маршрутов на странице.
type RouteFilterMode = 'all' | 'walk' | 'public_transport' | 'mixed'

export const RoutesListPage = () => {
  // Список маршрутов, загруженных с backend.
  const [routes, setRoutes] = useState<Route[]>([])

  // Флаг загрузки страницы.
  const [loading, setLoading] = useState(true)

  // Текст ошибки, если backend недоступен.
  const [error, setError] = useState<string | null>(null)

  // Активный фильтр по режиму маршрута.
  const [filterMode, setFilterMode] = useState<RouteFilterMode>('all')

  useEffect(() => {
    const loadRoutes = async () => {
      try {
        // Перед запросом включаем загрузку и сбрасываем старую ошибку.
        setLoading(true)
        setError(null)

        // Пока показываем маршруты только для Зеленоградска.
        const data = await getRoutesByCity('zelenogradsk')
        setRoutes(data)
      } catch (err) {
        console.error(err)
        setError('Не удалось загрузить маршруты с backend')
      } finally {
        setLoading(false)
      }
    }

    loadRoutes()
  }, [])

  // Отфильтрованный список маршрутов под текущий режим.
  const filteredRoutes = useMemo(() => {
    if (filterMode === 'all') {
      return routes
    }

    return routes.filter((route) => route.route_mode === filterMode)
  }, [routes, filterMode])

  return (
    <div className="app-screen">
      <div className="app-container">
        <AppHeader />

        <PageBreadcrumbs
          items={[
            { label: 'Home', to: '/' },
            { label: 'Routes' },
          ]}
        />

        <section className="places-list-panel">
          <SectionHeader
            eyebrow="Routes"
            title="Маршруты по городу"
            description="Список готовых сценариев: пешие прогулки, будущие транспортные маршруты и смешанные варианты."
          />

          <div
            style={{
              marginTop: '18px',
              display: 'flex',
              gap: '10px',
              flexWrap: 'wrap',
            }}
          >
            <button
              type="button"
              onClick={() => setFilterMode('all')}
              style={{
                padding: '10px 14px',
                borderRadius: '999px',
                border: '1px solid rgba(148, 163, 184, 0.18)',
                background: filterMode === 'all' ? '#dbeafe' : 'rgba(255,255,255,0.82)',
                color: '#0f172a',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Все
            </button>

            <button
              type="button"
              onClick={() => setFilterMode('walk')}
              style={{
                padding: '10px 14px',
                borderRadius: '999px',
                border: '1px solid rgba(148, 163, 184, 0.18)',
                background: filterMode === 'walk' ? '#dbeafe' : 'rgba(255,255,255,0.82)',
                color: '#0f172a',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Пешком
            </button>

            <button
              type="button"
              onClick={() => setFilterMode('public_transport')}
              style={{
                padding: '10px 14px',
                borderRadius: '999px',
                border: '1px solid rgba(148, 163, 184, 0.18)',
                background:
                  filterMode === 'public_transport' ? '#dbeafe' : 'rgba(255,255,255,0.82)',
                color: '#0f172a',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Общественный транспорт
            </button>

            <button
              type="button"
              onClick={() => setFilterMode('mixed')}
              style={{
                padding: '10px 14px',
                borderRadius: '999px',
                border: '1px solid rgba(148, 163, 184, 0.18)',
                background: filterMode === 'mixed' ? '#dbeafe' : 'rgba(255,255,255,0.82)',
                color: '#0f172a',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Смешанные
            </button>
          </div>
        </section>

        {loading && (
          <section style={{ marginTop: '18px' }}>
            <SurfaceCard style={{ padding: '20px' }}>
              <p style={{ margin: 0, color: '#64748b' }}>Загрузка маршрутов...</p>
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

        {!loading && !error && (
          <section
            style={{
              marginTop: '18px',
              display: 'grid',
              gap: '16px',
            }}
          >
            {filteredRoutes.map((route) => (
              <SurfaceCard
                key={route.id}
                style={{
                  padding: '20px',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    justifyContent: 'space-between',
                    gap: '12px',
                    flexWrap: 'wrap',
                  }}
                >
                  <div>
                    <h3
                      style={{
                        margin: 0,
                        fontSize: '26px',
                        lineHeight: 1.05,
                        letterSpacing: '-0.04em',
                        color: '#0f172a',
                      }}
                    >
                      {route.title}
                    </h3>

                    {route.short_description && (
                      <p
                        style={{
                          marginTop: '12px',
                          color: '#475569',
                          fontSize: '15px',
                          lineHeight: 1.6,
                        }}
                      >
                        {route.short_description}
                      </p>
                    )}
                  </div>

                  <Badge variant="brand">{getRouteModeLabel(route.route_mode)}</Badge>
                </div>

                <div
                  style={{
                    marginTop: '16px',
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '10px',
                  }}
                >
                  <Badge variant="neutral">
                    {route.duration_minutes ? `≈ ${route.duration_minutes} мин` : 'Без времени'}
                  </Badge>

                  <Badge variant="neutral">
                    {route.distance_km ? `≈ ${route.distance_km} км` : 'Без дистанции'}
                  </Badge>
                </div>

                <div
                  style={{
                    marginTop: '18px',
                    paddingTop: '14px',
                    borderTop: '1px solid #e2e8f0',
                  }}
                >
                  <Link
                    to={`/routes/${route.slug}`}
                    style={{
                      color: '#2563eb',
                      textDecoration: 'none',
                      fontWeight: 600,
                    }}
                  >
                    Открыть маршрут
                  </Link>
                </div>
              </SurfaceCard>
            ))}

            {!filteredRoutes.length && (
              <SurfaceCard style={{ padding: '20px' }}>
                <p style={{ margin: 0, color: '#64748b' }}>
                  Под выбранный режим маршруты пока не найдены.
                </p>
              </SurfaceCard>
            )}
          </section>
        )}
      </div>
    </div>
  )
}