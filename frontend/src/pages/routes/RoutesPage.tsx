import { AppHeader } from '../../components/ui/AppHeader'
import { Badge } from '../../components/ui/Badge'
import { PageBreadcrumbs } from '../../components/ui/PageBreadcrumbs'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { SurfaceCard } from '../../components/ui/SurfaceCard'

const routePoints = [
  {
    id: 1,
    title: 'Курортный проспект',
    description: 'Старт прогулки по центральной части города с архитектурой и туристической атмосферой.',
    duration: '15 мин',
  },
  {
    id: 2,
    title: 'Променад',
    description: 'Выход к морю, прогулка вдоль берега и обзор ключевых точек на набережной.',
    duration: '25 мин',
  },
  {
    id: 3,
    title: 'Пирс и видовая точка',
    description: 'Финальная остановка с открытым видом и хорошей точкой для паузы.',
    duration: '20 мин',
  },
]

export const WalkRoutePage = () => {
  return (
    <div className="app-screen">
      <div className="app-container">
        <AppHeader />

        <PageBreadcrumbs
          items={[
            { label: 'Home', to: '/' },
            { label: 'Walk Route' },
          ]}
        />

        <section className="places-list-panel">
          <SectionHeader
            eyebrow="Walking route"
            title="Пешая прогулка по достопримечательностям"
            description="Черновой MVP-экран под маршрутный сценарий. Позже сюда добавим реальные маршруты, общественный транспорт, длительность, расстояние и построение пути."
          />

          <div
            style={{
              marginTop: '18px',
              display: 'flex',
              gap: '10px',
              flexWrap: 'wrap',
            }}
          >
            <Badge variant="brand">Зеленоградск</Badge>
            <Badge variant="neutral">Пешком</Badge>
            <Badge variant="neutral">≈ 60 мин</Badge>
            <Badge variant="neutral">3 точки</Badge>
          </div>
        </section>

        <section
          style={{
            marginTop: '18px',
            display: 'grid',
            gap: '16px',
          }}
        >
          {routePoints.map((point, index) => (
            <SurfaceCard
              key={point.id}
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

                  <h3
                    style={{
                      margin: '8px 0 0',
                      fontSize: '26px',
                      lineHeight: 1.05,
                      letterSpacing: '-0.04em',
                      color: '#0f172a',
                    }}
                  >
                    {point.title}
                  </h3>
                </div>

                <Badge variant="success">{point.duration}</Badge>
              </div>

              <p
                style={{
                  marginTop: '14px',
                  color: '#475569',
                  fontSize: '15px',
                  lineHeight: 1.6,
                }}
              >
                {point.description}
              </p>
            </SurfaceCard>
          ))}
        </section>
      </div>
    </div>
  )
}