import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { adminGet } from './adminApi'
import type { AdminImportJobDiagnostic, AdminImportJobTimelineEvent } from './adminTypes'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

const STATUS_LABELS: Record<string, string> = {
  queued: 'В очереди',
  running: 'Выполняется',
  success: 'Завершён',
  success_with_warnings: 'Завершён с предупреждениями',
  partial_success: 'Частично завершён',
  failed: 'Ошибка',
  cancelled: 'Отменён',
  stalled: 'Завис',
}

const SEVERITY_TONE: Record<string, string> = {
  error: 'admin-state-error',
  warning: 'admin-state-warning',
  info: 'admin-state',
}

const statusLabel = (status: string) => STATUS_LABELS[status] ?? status
const formatDateTime = (value: string | null) => {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
const formatDuration = (seconds: number | null) => {
  if (seconds == null) return '—'
  if (seconds < 60) return `${seconds} с`
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return `${minutes} мин ${rest} с`
}

const TimelineCard = ({ event }: { event: AdminImportJobTimelineEvent }) => (
  <article className={`admin-import-timeline-card ${SEVERITY_TONE[event.severity] ?? 'admin-state'}`} data-testid="diagnostic-timeline-event">
    <div className="admin-import-timeline-head">
      <span className="admin-badge">{event.type}</span>
      <span className="admin-muted">{formatDateTime(event.timestamp)}</span>
    </div>
    <p>{event.summary}</p>
    {event.payload ? (
      <details>
        <summary>Данные события</summary>
        <pre>{JSON.stringify(event.payload, null, 2)}</pre>
      </details>
    ) : null}
  </article>
)

export const AdminImportJobDiagnosticPage = () => {
  const { jobId = '' } = useParams()
  const [diagnostic, setDiagnostic] = useState<AdminImportJobDiagnostic | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [copyStatus, setCopyStatus] = useState<string | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    adminGet<AdminImportJobDiagnostic>(`/admin/import-jobs/${jobId}/diagnostic`, { cache: false })
      .then(setDiagnostic)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [jobId])

  useEffect(() => { load() }, [load])

  const copyReport = async () => {
    if (!diagnostic) return
    try {
      await navigator.clipboard?.writeText(diagnostic.diagnostic_report)
      setCopyStatus('Отчёт скопирован')
    } catch {
      setCopyStatus('Не удалось скопировать отчёт')
    }
  }

  return (
    <div className="admin-import-diagnostic-page">
      <h2 className="admin-page-title">Диагностика запуска #{jobId}</h2>
      {error && <AdminError message={error} />}
      {loading ? (
        <AdminLoading />
      ) : !diagnostic ? (
        <AdminEmpty message="Задача не найдена" />
      ) : (
        <>
          <section className="admin-import-diagnostic-summary" data-testid="diagnostic-summary">
            <div className="admin-import-diagnostic-summary-top">
              <div>
                <strong>{diagnostic.city_name}</strong>
                <div className="admin-muted">{diagnostic.city_slug} · запуск #{diagnostic.job_id}</div>
              </div>
              <span className={`admin-badge pub-${diagnostic.status === 'failed' || diagnostic.status === 'stalled' ? 'hidden' : diagnostic.status === 'success' ? 'published' : 'draft'}`}>
                {statusLabel(diagnostic.status)}
              </span>
            </div>
            <p>Текущий шаг: <strong>{diagnostic.current_step}</strong></p>
            {diagnostic.last_completed_step && <p>Последний завершённый шаг: <strong>{diagnostic.last_completed_step}</strong></p>}
            {diagnostic.failure_reason && (
              <p className="admin-error-text" data-testid="diagnostic-failure-reason">{diagnostic.failure_reason}</p>
            )}
            <p className="admin-muted">Начало: {formatDateTime(diagnostic.started_at)}</p>
            <p className="admin-muted">Завершение: {formatDateTime(diagnostic.finished_at)}</p>
            <p className="admin-muted">Длительность: {formatDuration(diagnostic.duration_seconds)}</p>
            {diagnostic.worker_state && <p className="admin-muted">Состояние worker: {diagnostic.worker_state}{diagnostic.worker_run_id ? ` · run ${diagnostic.worker_run_id}` : ''}</p>}
            {diagnostic.stop_reason && <p className="admin-muted" data-testid="diagnostic-stop-reason">Причина остановки: {diagnostic.stop_reason}{diagnostic.stop_source ? ` (${diagnostic.stop_source})` : ''}</p>}
            {diagnostic.exit_code != null && <p className="admin-muted">Код завершения: {diagnostic.exit_code}{diagnostic.oom_killed ? ' · OOM' : ''}</p>}
            {diagnostic.workflow_run_url && (
              <p className="admin-muted">
                Workflow: <a href={diagnostic.workflow_run_url} target="_blank" rel="noreferrer">{diagnostic.workflow_name ?? diagnostic.workflow_run_id ?? 'открыть'}</a>
              </p>
            )}
            <button type="button" className="admin-btn admin-btn-primary admin-btn-lg" onClick={() => void copyReport()} data-testid="copy-diagnostic-report">
              Копировать диагностический отчёт
            </button>
            {copyStatus && <p className="admin-success-text">{copyStatus}</p>}
          </section>

          <section className="admin-import-diagnostic-timeline" data-testid="diagnostic-timeline">
            <div className="admin-help-title">Хронология</div>
            {diagnostic.timeline.length === 0 ? (
              <p className="admin-muted">Событий по этому запуску пока нет.</p>
            ) : (
              diagnostic.timeline.map((event, index) => <TimelineCard event={event} key={index} />)
            )}
          </section>

          <details className="admin-import-diagnostic-raw">
            <summary>Полные данные (JSON)</summary>
            <pre>{JSON.stringify(diagnostic, null, 2)}</pre>
          </details>

          <Link className="admin-btn admin-btn-sm" to="/admin/imports">Назад к списку импортов</Link>
        </>
      )}
    </div>
  )
}
