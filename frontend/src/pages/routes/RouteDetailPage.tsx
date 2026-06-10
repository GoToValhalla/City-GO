import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getRouteBySlug } from '../../api/routes/routes.api'
import type { RouteDetail } from '../../api/routes/routes.api'
import { AppHeader } from '../../components/ui/AppHeader'
import { Badge } from '../../components/ui/Badge'
import { PageBreadcrumbs } from '../../components/ui/PageBreadcrumbs'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { SurfaceCard } from '../../components/ui/SurfaceCard'
import { getRouteModeLabel } from '../../features/routes/model/getRouteModeLabel'

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

        {!loading && !error && (
          <section
            style={{
              marginTop: '18px',
              display: 'grid',
              gap: '16px',
            }}
          >
            {(route?.points ?? []).map((point, index) => (
              <SurfaceCard
                key={`${point.place_id}-${point.position}`}
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
                    <div
                      style={{
                        fontSize: '13px',
                        fontWeight: 700,
                        letterSpacing: '0.08em',
                        textTransform: 'uppercase',
                        color: '#64748b',
                      }}
                    >
                      Точка {index + 1}
                    </div>

                    {point.place_slug ? (
                      <Link
                        to={`/places/${point.place_slug}`}
                        style={{
                          display: 'inline-block',
                          marginTop: '8px',
                          fontSize: '26px',
                          lineHeight: 1.05,
                          letterSpacing: '-0.04em',
                          color: '#0f172a',
                          textDecoration: 'none',
                          fontWeight: 700,
                        }}
                      >
                        {point.place_title ?? `Place #${point.place_id}`}
                      </Link>
                    ) : (
                      <h3
                        style={{
                          margin: '8px 0 0',
                          fontSize: '26px',
                          lineHeight: 1.05,
                          letterSpacing: '-0.04em',
                          color: '#0f172a',
                        }}
                      >
                        {point.place_title ?? `Place #${point.place_id}`}
                      </h3>
                    )}
                  </div>

                  <Badge variant="success">#{point.position}</Badge>
                </div>

                {point.place_slug && (
                  <p
                    style={{
                      marginTop: '14px',
                      color: '#475569',
                      fontSize: '15px',
                      lineHeight: 1.6,
                    }}
                  >
                    <Link
                      to={`/places/${point.place_slug}`}
                      style={{
                        color: '#2563eb',
                        textDecoration: 'none',
                        fontWeight: 600,
                      }}
                    >
                      Открыть точку маршрута
                    </Link>
                  </p>
                )}
              </SurfaceCard>
            ))}
          </section>
        )}
      </div>
    </div>
  )
}