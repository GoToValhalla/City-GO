import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { adminGet } from './adminApi'
import type { AdminImportJobAttempt, AdminImportJobDiagnostic, AdminImportJobTimelineEvent } from './adminTypes'
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

// partial_success is neither a failure nor a plain success — it must render
// with its own distinct (warning) tone, never green "published"/success and
// never red "hidden"/failure, so an operator never mistakes it for either.
const statusBadgeTone = (status: string): string => {
  if (status === 'failed' || status === 'stalled') return 'hidden'
  if (status === 'partial_success') return 'draft'
  if (status === 'success') return 'published'
  return 'draft'
}

const ATTEMPT_RESULT_LABELS: Record<string, string> = {
  worker_job_finished: 'Успешно',
  worker_job_failed: 'Ошибка',
  worker_job_stalled: 'Завис',
  import_job_cancelled: 'Отменён',
  in_progress: 'Выполняется',
  worker_crashed_no_terminal_event: 'Воркер прервался без финального события',
}
const attemptResultLabel = (result: string | null) => result == null ? '—' : ATTEMPT_RESULT_LABELS[result] ?? result

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

// Attempts are the immutable retry-history reconstruction from durable
// system_logs (see services/admin_import_job_diagnostic_service.py
// _job_attempts) — distinct from the job's own current, mutable
// status/started_at/finished_at columns above. A job can have been retried
// several times; each past attempt is a fact that does not change even
// after the job's live status moves on.
const AttemptCard = ({ attempt }: { attempt: AdminImportJobAttempt }) => (
  <article className="admin-import-timeline-card admin-state" data-testid="diagnostic-attempt-card">
    <div className="admin-import-timeline-head">
      <span className="admin-badge">Попытка №{attempt.attempt_number}</span>
      <span className="admin-muted">{formatDateTime(attempt.started_at)}</span>
    </div>
    <p>Результат: <strong>{attemptResultLabel(attempt.result)}</strong></p>
    {attempt.ended_at && <p className="admin-muted">Завершена: {formatDateTime(attempt.ended_at)}</p>}
    {attempt.retry_count_at_claim != null && <p className="admin-muted">retry_count на момент захвата: {attempt.retry_count_at_claim}</p>}
  </article>
)

export const AdminImportJobDiagnosticPage = () => {
  const { jobId = '' } = useParams()
  const [diagnostic, setDiagnostic] = useState<AdminImportJobDiagnostic | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [copyStatus, setCopyStatus] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    void (async () => {
      await Promise.resolve()
      if (!alive) return
      setLoading(true)
      setError(null)
      const result = await adminGet<AdminImportJobDiagnostic>(`/admin/import-jobs/${jobId}/diagnostic`, { cache: false })
      if (alive) setDiagnostic(result)
    })()
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false))
    return () => { alive = false }
  }, [jobId])

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
              <span className={`admin-badge pub-${statusBadgeTone(diagnostic.status)}`} data-testid="diagnostic-status-badge">
                {statusLabel(diagnostic.status)}
              </span>
            </div>
            <p>Текущий шаг: <strong>{diagnostic.current_step}</strong></p>
            {diagnostic.last_completed_step && <p>Последний завершённый шаг: <strong>{diagnostic.last_completed_step}</strong></p>}
            {diagnostic.failure_reason && (
              <p className="admin-error-text" data-testid="diagnostic-failure-reason">{diagnostic.failure_reason}</p>
            )}
            {diagnostic.partial_success_reason && (
              <p className="admin-error-text" data-testid="diagnostic-partial-success-reason">Причина частичного завершения: {diagnostic.partial_success_reason}</p>
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
            {/* diagnostic.status (the job's own truthful outcome) and
                diagnostic.exit_code/stop_reason/oom_killed above are two
                genuinely distinct, separately-persisted facts, deliberately
                never merged into a single derived "did it succeed" verdict —
                only the GitHub Actions run itself is authoritative for
                whether the workflow passed or failed; that conclusion is not
                duplicated or predicted here. */}
            <button type="button" className="admin-btn admin-btn-primary admin-btn-lg" onClick={() => void copyReport()} data-testid="copy-diagnostic-report">
              Копировать диагностический отчёт
            </button>
            {copyStatus && <p className="admin-success-text">{copyStatus}</p>}
          </section>

          {diagnostic.failed_steps.length > 0 && (
            <section className="admin-help-panel" data-testid="diagnostic-failed-steps">
              <div className="admin-help-title">Шаги с ошибкой</div>
              {diagnostic.failed_steps.map((step, index) => (
                <p key={index}>
                  <strong>{step.step_label}</strong>{step.error_message ? `: ${step.error_message}` : ''}
                </p>
              ))}
            </section>
          )}

          <section className="admin-import-diagnostic-timeline" data-testid="diagnostic-attempts">
            <div className="admin-help-title">Попытки (история, не текущий статус)</div>
            {diagnostic.attempts.length === 0 ? (
              <p className="admin-muted">Worker ещё не захватывал эту задачу — попыток пока 0.</p>
            ) : (
              diagnostic.attempts.map((attempt) => <AttemptCard attempt={attempt} key={attempt.attempt_number} />)
            )}
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
