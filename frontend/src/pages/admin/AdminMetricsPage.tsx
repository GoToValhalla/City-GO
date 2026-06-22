import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import { AdminError, AdminLoading } from './shared/AdminStates'

type Metrics = {
  dau: number; mau: number; routes_built: number; routes_failed: number; avg_route_stops: number
  routes_today?: number; routes_week?: number; routes_failed_week?: number; route_success_rate?: number | null
  places_total?: number; places_published?: number; places_no_photo?: number; places_no_address?: number
  places_no_description?: number; imports_ok_week?: number; imports_fail_week?: number
  enrichment_ok_week?: number; ai_requests_week?: number; data_collection_note: string
}

type DeploymentStatus = {
  enabled: boolean
  mode: string
  repo: string
  workflow: string
  branch: string
  token_configured: boolean
  token_env_key?: string | null
  action: string
  deploy_note: string
}

type DeploymentRunResponse = {
  status: string
  github_status_code: number
  repo: string
  workflow: string
  branch: string
}

type MetricCard = { label: string; value: number | string; link?: string; action?: string }

export const AdminMetricsPage = () => {
  const [data, setData] = useState<Metrics | null>(null)
  const [deployment, setDeployment] = useState<DeploymentStatus | null>(null)
  const [deployMessage, setDeployMessage] = useState<string | null>(null)
  const [deployLoading, setDeployLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      adminGet<Metrics>('/admin/metrics/summary'),
      adminGet<DeploymentStatus>('/admin/deployment/status').catch(() => null),
    ])
      .then(([metrics, deploymentStatus]) => {
        setData(metrics)
        setDeployment(deploymentStatus)
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const runCi = async () => {
    try {
      setDeployLoading(true)
      setDeployMessage('Запускаю проверку в GitHub...')
      const response = await adminPost<DeploymentRunResponse>('/admin/deployment/run-ci', { confirm: true })
      setDeployMessage(`Запущено: ${response.workflow} · ветка ${response.branch} · ${response.status}`)
    } catch (e) {
      setDeployMessage(e instanceof Error ? e.message : 'Не удалось запустить проверку')
    } finally {
      setDeployLoading(false)
    }
  }

  if (loading) return <AdminLoading />
  if (error) return <AdminError message={error} />
  if (!data) return null

  const dataQuality: MetricCard[] = [
    { label: 'Без фото', value: data.places_no_photo ?? 0, link: '/admin/places?preset=no_photo', action: 'Открыть' },
    { label: 'Без адреса', value: data.places_no_address ?? 0, link: '/admin/places?preset=no_address', action: 'Открыть' },
    { label: 'Без описания', value: data.places_no_description ?? 0, link: '/admin/places?preset=no_description', action: 'Открыть' },
  ]
  const routes: MetricCard[] = [
    { label: 'Маршрутов за 7 дней', value: data.routes_week ?? 0, link: '/admin/routes/dry-run', action: 'Проверить сборку' },
    { label: 'Ошибок маршрутов за 7 дней', value: data.routes_failed_week ?? 0, link: '/admin/routes/eligibility', action: 'Диагностика' },
    { label: 'Успешность', value: data.route_success_rate ?? '—' },
  ]
  const imports: MetricCard[] = [
    { label: 'Успешных импортов за 7 дней', value: data.imports_ok_week ?? 0, link: '/admin/imports', action: 'Импорты' },
    { label: 'Импортов с ошибкой за 7 дней', value: data.imports_fail_week ?? 0, link: '/admin/imports', action: 'Проверить' },
    { label: 'Обогащений за 7 дней', value: data.enrichment_ok_week ?? 0, link: '/admin/place-enrichment', action: 'Экспорт' },
  ]

  const renderSection = (title: string, cards: MetricCard[]) => (
    <section>
      <h3 className="admin-page-subtitle">{title}</h3>
      <div className="admin-metrics-grid">
        {cards.map((c) => (
          <div key={c.label} className="admin-metric-card">
            <div className="admin-metric-value">{c.value}</div>
            <div className="admin-metric-label">{c.label}</div>
            {c.link && <Link className="admin-btn admin-btn-sm" to={c.link}>{c.action ?? 'Открыть'}</Link>}
          </div>
        ))}
      </div>
    </section>
  )

  return (
    <div>
      <h2 className="admin-page-title">Метрики</h2>
      <p className="admin-page-subtitle">{data.data_collection_note}</p>
      {renderSection('Качество данных', dataQuality)}
      {renderSection('Маршруты', routes)}
      {renderSection('Импорты и обогащение', imports)}
      <section>
        <h3 className="admin-page-subtitle">Проверка и деплой</h3>
        <div className="admin-metrics-grid">
          <div className="admin-metric-card">
            <div className="admin-metric-value">{deployment?.enabled ? 'Готово' : 'Не настроено'}</div>
            <div className="admin-metric-label">Проверка в GitHub</div>
            <p className="admin-muted">
              {deployment
                ? `${deployment.repo} · ${deployment.workflow} · ${deployment.branch}`
                : 'Сервер не вернул статус проверки.'}
            </p>
            <p className="admin-muted">{deployment?.deploy_note ?? 'Для запуска нужен endpoint на сервере и GitHub token.'}</p>
            <button
              type="button"
              className="admin-btn admin-btn-primary"
              disabled={!deployment?.enabled || deployLoading}
              onClick={() => void runCi()}
            >
              {deployLoading ? 'Запускаю...' : 'Запустить проверку'}
            </button>
            {deployMessage ? <p className="admin-muted">{deployMessage}</p> : null}
          </div>
        </div>
      </section>
      <section>
        <h3 className="admin-page-subtitle">Продуктовые метрики</h3>
        <div className="admin-metrics-grid">
          <div className="admin-metric-card"><div className="admin-metric-value">{data.dau}</div><div className="admin-metric-label">Активных за день</div></div>
          <div className="admin-metric-card"><div className="admin-metric-value">{data.mau}</div><div className="admin-metric-label">Активных за месяц</div></div>
        </div>
      </section>
    </div>
  )
}
