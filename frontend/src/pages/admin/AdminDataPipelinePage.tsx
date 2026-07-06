import { useCallback, useEffect, useState } from 'react'
import { adminGet } from './adminApi'
import { AdminLoading, AdminSectionError } from './shared/AdminStates'
import './AdminDataPipeline.css'

type QueueRow = {
  code: string
  label: string
  pending_count: number
  running_count: number
  failed_count: number
  status: string
  updated_at: string | null
}

type RecentRun = {
  run_id: number
  run_type_label: string
  city_name: string | null
  status_label: string
  duration_seconds: number | null
  error_summary: string | null
}

type PipelineStatus = {
  overall_status: string
  degraded_sections: string[]
  metrics: Record<string, number>
  queues: QueueRow[]
  recent_runs: RecentRun[]
  fetched_at: string
}

const STATUS_LABELS: Record<string, string> = {
  healthy: 'В норме',
  partial_degraded: 'Частичная деградация',
  full_degraded: 'Сильная деградация',
  empty: 'Нет данных',
}

const formatTime = (value: string | null) => {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString('ru-RU')
}

export const AdminDataPipelinePage = () => {
  const [status, setStatus] = useState<PipelineStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true)
    else setLoading(true)
    setError(null)
    try {
      const payload = await adminGet<PipelineStatus>('/admin/data-pipeline/status')
      setStatus(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Сбой выполнения операции. Повторите попытку через минуту или обратитесь в поддержку.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  if (loading && !status) return <AdminLoading message="Загрузка данных из реестра..." />
  if (error && !status) {
    return (
      <AdminSectionError
        title="Не удалось загрузить мониторинг"
        message={error}
        onRetry={() => void load()}
      />
    )
  }

  return (
    <div className="admin-data-pipeline" data-testid="admin-data-pipeline">
      <header className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Мониторинг конвейера данных</h1>
          <p className="admin-page-subtitle">Только чтение. Обновление не запускает импорт и не меняет очереди.</p>
        </div>
        <button type="button" className="admin-btn admin-btn-safe" disabled={refreshing} onClick={() => void load(true)}>
          {refreshing ? 'Обновление…' : 'Обновить данные мониторинга'}
        </button>
      </header>

      {error ? <div className="admin-state admin-state-error">{error}</div> : null}

      {status?.overall_status === 'partial_degraded' || status?.overall_status === 'full_degraded' ? (
        <div className="admin-state admin-state-warning">
          Часть данных временно недоступна. Отображаются последние доступные сведения.
          {status.degraded_sections.length > 0 ? ` Затронуто: ${status.degraded_sections.join(', ')}.` : ''}
        </div>
      ) : null}

      <section className="admin-section admin-readonly-zone">
        <h2 className="admin-section-title">Сводка</h2>
        <div className="admin-metrics-grid">
          <article className="admin-metric-card">
            <span className="admin-muted">Общий статус</span>
            <strong>{STATUS_LABELS[status?.overall_status ?? 'empty']}</strong>
          </article>
          <article className="admin-metric-card">
            <span className="admin-muted">Мест без координат</span>
            <strong>{status?.metrics.places_without_coordinates ?? 0}</strong>
          </article>
          <article className="admin-metric-card">
            <span className="admin-muted">Готово к маршрутам</span>
            <strong>{status?.metrics.places_route_eligible ?? 0}</strong>
          </article>
          <article className="admin-metric-card">
            <span className="admin-muted">На слияние данных</span>
            <strong>{status?.metrics.pending_merge_reviews ?? 0}</strong>
          </article>
          <article className="admin-metric-card">
            <span className="admin-muted">Обновлено</span>
            <strong>{formatTime(status?.fetched_at ?? null)}</strong>
          </article>
        </div>
      </section>

      <section className="admin-section admin-readonly-zone">
        <h2 className="admin-section-title">Очереди</h2>
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Очередь</th><th>В ожидании</th><th>В работе</th><th>Ошибки</th><th>Состояние</th></tr></thead>
            <tbody>
              {(status?.queues ?? []).map((row) => (
                <tr key={row.code}>
                  <td>{row.label}</td>
                  <td>{row.pending_count}</td>
                  <td>{row.running_count}</td>
                  <td>{row.failed_count}</td>
                  <td>{row.status === 'error' ? 'Требует внимания' : row.status === 'warning' ? 'Нагрузка' : row.status === 'ok' ? 'Активна' : 'Спокойно'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="admin-section admin-readonly-zone">
        <h2 className="admin-section-title">Недавние запуски</h2>
        {!status?.recent_runs.length ? (
          <p className="admin-muted">Запусков пока нет.</p>
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead><tr><th>Запуск</th><th>Город</th><th>Статус</th><th>Длительность</th><th>Ошибка</th></tr></thead>
              <tbody>
                {status.recent_runs.map((run) => (
                  <tr key={`${run.run_id}-${run.run_type_label}`}>
                    <td>#{run.run_id} · {run.run_type_label}</td>
                    <td>{run.city_name ?? '—'}</td>
                    <td>{run.status_label}</td>
                    <td>{run.duration_seconds != null ? `${run.duration_seconds} с` : '—'}</td>
                    <td>{run.error_summary ?? '—'}</td>
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
