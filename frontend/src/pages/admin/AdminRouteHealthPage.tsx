import { useCallback, useEffect, useState } from 'react'
import { adminGet, adminPost } from './adminApi'
import { AdminLoading, AdminSectionError } from './shared/AdminStates'

type RouteHealthIssue = {
  code: string
  label: string
  severity: 'critical' | 'warning' | 'ok'
  route_id: number
  route_title: string
  details: Record<string, unknown>
}

type RouteHealthSummary = {
  city_slug: string | null
  checked_at: string
  routes_checked: number
  critical_count: number
  warning_count: number
  status: 'healthy' | 'warning' | 'critical'
  issues: RouteHealthIssue[]
}

const STATUS_LABELS: Record<RouteHealthSummary['status'], string> = {
  healthy: 'Маршруты в норме',
  warning: 'Есть предупреждения',
  critical: 'Есть критические ошибки',
}

const ISSUE_LABELS: Record<string, string> = {
  route_min_points_failed: 'Маршрут содержит меньше 3 туристических точек',
  route_service_places_detected: 'Маршрут содержит служебные места',
  route_city_mixing_error: 'Маршрут смешивает города',
  route_long_transition_warning: 'Слишком длинный переход',
  route_low_diversity_warning: 'Слабое разнообразие категорий',
}

const numberDetail = (details: Record<string, unknown>, key: string) => {
  const value = details[key]
  return typeof value === 'number' ? value : null
}

const arrayDetailCount = (details: Record<string, unknown>, key: string) => {
  const value = details[key]
  return Array.isArray(value) ? value.length : null
}

const issueDetailsText = (issue: RouteHealthIssue) => {
  if (issue.code === 'route_min_points_failed') {
    const tourist = numberDetail(issue.details, 'tourist_points')
    const minimum = numberDetail(issue.details, 'minimum')
    return `Туристических точек: ${tourist ?? 0}; минимум: ${minimum ?? 3}`
  }
  if (issue.code === 'route_service_places_detected') {
    const total = numberDetail(issue.details, 'total')
    return `Служебных точек: ${total ?? 'нужно проверить'}`
  }
  if (issue.code === 'route_city_mixing_error') {
    const total = arrayDetailCount(issue.details, 'place_ids')
    return `Точек из другого города: ${total ?? 'нужно проверить'}`
  }
  if (issue.code === 'route_long_transition_warning') {
    const distance = numberDetail(issue.details, 'distance_km')
    return distance === null ? 'Проверьте длину перехода' : `Длина маршрута: ${distance.toFixed(1)} км`
  }
  if (issue.code === 'route_low_diversity_warning') {
    return 'Проверьте разнообразие категорий в маршруте'
  }
  return 'Подробности доступны в backend-диагностике'
}

export const AdminRouteHealthPage = () => {
  const [state, setState] = useState<RouteHealthSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setState(await adminGet<RouteHealthSummary>('/admin/route-health'))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить диагностику маршрутов')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const rerun = async () => {
    if (refreshing) return
    setRefreshing(true)
    setError(null)
    try {
      const payload = await adminPost<{ result: RouteHealthSummary }>('/admin/route-health/re-run', {})
      setState(payload.result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось перезапустить диагностику маршрутов')
    } finally {
      setRefreshing(false)
    }
  }

  if (loading && !state) return <AdminLoading message="Загрузка диагностики маршрутов..." />
  if (error && !state) return <AdminSectionError title="Диагностика маршрутов недоступна" message={error} onRetry={() => void load()} />

  return (
    <div className="admin-page admin-route-health-page" data-testid="admin-route-health-page">
      <header className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Диагностика маршрутов</h1>
          <p className="admin-page-subtitle">Backend-only проверки. Интерфейс только отображает результат и запускает безопасный повтор проверки.</p>
        </div>
        <button type="button" className="admin-btn admin-btn-safe" disabled={refreshing} onClick={() => void rerun()}>
          {refreshing ? 'Проверка выполняется…' : 'Перезапустить диагностику'}
        </button>
      </header>

      {error ? <div className="admin-state admin-state-error">{error}</div> : null}

      <section className="admin-section admin-readonly-zone">
        <h2 className="admin-section-title">Сводка</h2>
        <div className="admin-metrics-grid">
          <article className="admin-metric-card"><span className="admin-muted">Статус</span><strong>{STATUS_LABELS[state?.status ?? 'healthy']}</strong></article>
          <article className="admin-metric-card"><span className="admin-muted">Проверено маршрутов</span><strong>{state?.routes_checked ?? 0}</strong></article>
          <article className="admin-metric-card"><span className="admin-muted">Критические ошибки</span><strong>{state?.critical_count ?? 0}</strong></article>
          <article className="admin-metric-card"><span className="admin-muted">Предупреждения</span><strong>{state?.warning_count ?? 0}</strong></article>
        </div>
      </section>

      <section className="admin-section admin-readonly-zone">
        <h2 className="admin-section-title">Найденные проблемы</h2>
        {!state?.issues.length ? <p className="admin-muted">Критических проблем маршрутов не найдено.</p> : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead><tr><th>Маршрут</th><th>Уровень</th><th>Проблема</th><th>Детали</th></tr></thead>
              <tbody>
                {state.issues.map((issue) => (
                  <tr key={`${issue.route_id}-${issue.code}`}>
                    <td>{issue.route_title}</td>
                    <td>{issue.severity === 'critical' ? 'Критично' : issue.severity === 'warning' ? 'Предупреждение' : 'Норма'}</td>
                    <td>{ISSUE_LABELS[issue.code] ?? issue.label}</td>
                    <td>{issueDetailsText(issue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
