import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminGet, adminPost, adminPostLong } from './adminApi'
import { AdminError, AdminLoading, AdminSectionError } from './shared/AdminStates'

type ActionCard = {
  code: string
  title: string
  count: number
  severity: string
  link_path: string
  hint?: string | null
  action_label?: string | null
  short_hint?: string | null
  queue_type?: string
  primary_action?: string
  sample_endpoint?: string | null
  owner?: string
  is_human_actionable?: boolean
  mobile_priority?: string
}
type Overview = { critical: ActionCard[]; data_quality: ActionCard[]; operations: ActionCard[]; recent_audit_count: number }
type BacklogReason = { code: string; title: string; count: number; auto_fixable: boolean; manual_required: boolean; sample_endpoint?: string | null }
type BacklogQueue = {
  code: string
  title: string
  total_count: number
  unique_places_count: number
  auto_fixable_count: number
  manual_count: number
  overlap_count: number
  recommended_action: string
  reasons: BacklogReason[]
}
type BacklogBreakdown = {
  summary: {
    unique_problem_places: number
    total_problem_signals: number
    route_blocker_places: number
    auto_fixable_places: number
    manual_places: number
    verification_backlog_places: number
    content_gap_places: number
  }
  queues: BacklogQueue[]
  overlaps: { left: string; right: string; count: number }[]
}
type ReductionAction = {
  code: string
  title: string
  description: string
  expected_effect: string
  enabled: boolean
  disabled_reason?: string | null
  affected_count: number
  max_batch_size: number
}
type ReductionPlan = {
  summary: Record<string, number>
  actions: ReductionAction[]
}
type ReductionResult = {
  action_code: string
  status: string
  dry_run: boolean
  affected_count: number
  would_change_count?: number
  changed_count: number
  skipped_count: number
  failed_count: number
  queued_count: number
  message: string
  job_id?: number
  audit_id?: number
}
type ReductionRun = {
  job_id: number
  status: string
  action_code?: string | null
  actor?: string | null
  started_at?: string | null
  finished_at?: string | null
  limit?: number
  affected_count: number
  changed_count: number
  queued_count: number
  skipped_count: number
  failed_count: number
  message?: string | null
}
type ReductionTaskStat = {
  task_type: string
  total_count: number
  active_count: number
  statuses: Record<string, number>
}
type ReductionReport = {
  summary: {
    runs_24h: number
    runs_7d: number
    queued_24h: number
    queued_7d: number
    skipped_24h: number
    skipped_7d: number
    failed_24h: number
    failed_7d: number
    tasks_created_24h: number
    tasks_created_7d: number
    active_tasks: number
  }
  last_result: ReductionRun | null
  task_stats: ReductionTaskStat[]
  recent_runs: ReductionRun[]
}
type FullSafeRunStep = {
  action_code: string
  title?: string | null
  status: string
  affected_count: number
  changed_count: number
  queued_count: number
  skipped_count: number
  failed_count: number
  started_at?: string | null
  finished_at?: string | null
  message?: string | null
}
type FullSafeRun = {
  job_id: number
  status: string
  runtime_status: string
  is_running: boolean
  is_stale: boolean
  created_at?: string | null
  updated_at?: string | null
  actor?: string | null
  action_code?: string | null
  status_label?: string | null
  started_at?: string | null
  finished_at?: string | null
  last_heartbeat_at?: string | null
  total_actions: number
  processed_actions: number
  remaining_actions: number
  affected_count: number
  changed_count: number
  queued_count: number
  skipped_count: number
  failed_count: number
  remaining_count: number
  stop_requested: boolean
  actions: FullSafeRunStep[]
}
type FullSafeReductionAction = typeof FULL_SAFE_REDUCTION_ACTIONS[number]

const FULL_SAFE_REDUCTION_ACTIONS = [
  'enqueue_photo_discovery',
  'enqueue_address_recovery',
  'enqueue_description_enrichment',
  'auto_recheck_verification_backlog',
] as const
const BACKLOG_REDUCTION_APPLY_PATH = '/admin/overview/backlog-reduction/apply'
const FULL_SAFE_RUN_PATH = '/admin/overview/backlog-reduction/full-safe-run'
const FULL_SAFE_RUN_LATEST_PATH = `${FULL_SAFE_RUN_PATH}/latest`
const FULL_SAFE_REDUCTION_LIMIT = 500
const ACTION_TITLES: Record<string, string> = {
  enqueue_photo_discovery: 'Фото',
  enqueue_address_recovery: 'Адреса',
  enqueue_description_enrichment: 'Описания',
  auto_recheck_verification_backlog: 'Перепроверка данных',
  recompute_route_eligibility: 'Проверка маршрутов',
  exclude_service_places_from_routes: 'Служебные места',
  classify_unknown_categories_deterministic: 'Категории',
  normalize_manual_review_backlog: 'Ручной разбор',
  recompute_low_confidence: 'Низкая уверенность',
}
const STATUS_TITLES: Record<string, string> = {
  pending: 'Ожидает',
  running: 'В работе',
  queued: 'В очереди',
  processing: 'Обрабатывается',
  locked: 'Занято',
  stop_requested: 'Остановка запрошена',
  stopped: 'Остановлен',
  stuck: 'Нет прогресса',
  applied: 'Готово',
  completed: 'Готово',
  partial: 'Частично',
  failed: 'Ошибка',
  unsupported: 'Не поддержано',
}

const severityClass = (s: string) => `admin-severity admin-severity-${s}`
const actionLabel = (card: ActionCard) => card.action_label || 'Открыть выборку'
const errorMessage = (error: unknown) => (error instanceof Error ? error.message : 'Не удалось загрузить данные')
const formatDate = (value?: string | null) => {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('ru-RU')
}
const statusTitle = (status?: string | null) => STATUS_TITLES[status ?? ''] ?? 'Неизвестно'
const actionTitle = (code?: string | null, fallback?: string | null) => fallback || ACTION_TITLES[code ?? ''] || 'Действие'
const normalizeFullSafeRun = (run: FullSafeRun | null): FullSafeRun | null => {
  if (!run) return null
  return {
    ...run,
    total_actions: Number(run.total_actions || 0),
    processed_actions: Number(run.processed_actions || 0),
    remaining_actions: Number(run.remaining_actions || 0),
    affected_count: Number(run.affected_count || 0),
    changed_count: Number(run.changed_count || 0),
    queued_count: Number(run.queued_count || 0),
    skipped_count: Number(run.skipped_count || 0),
    failed_count: Number(run.failed_count || 0),
    remaining_count: Number(run.remaining_count || 0),
    actions: Array.isArray(run.actions) ? run.actions : [],
  }
}

export const AdminOverviewPage = () => {
  const [data, setData] = useState<Overview | null>(null)
  const [breakdown, setBreakdown] = useState<BacklogBreakdown | null>(null)
  const [plan, setPlan] = useState<ReductionPlan | null>(null)
  const [report, setReport] = useState<ReductionReport | null>(null)
  const [selectedAction, setSelectedAction] = useState<string>('')
  const [limit, setLimit] = useState(100)
  const [confirmation, setConfirmation] = useState('')
  const [runningAction, setRunningAction] = useState<string | null>(null)
  const [fullSafeRun, setFullSafeRun] = useState<FullSafeRun | null>(null)
  const [fullSafeRunRunning, setFullSafeRunRunning] = useState(false)
  const [fullSafeRunRefreshing, setFullSafeRunRefreshing] = useState(false)
  const [fullSafeRunStopping, setFullSafeRunStopping] = useState(false)
  const [fullSafeRunError, setFullSafeRunError] = useState<string | null>(null)
  const [reductionResult, setReductionResult] = useState<ReductionResult | null>(null)
  const [reductionError, setReductionError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [detailsError, setDetailsError] = useState<string | null>(null)
  const [detailsLoading, setDetailsLoading] = useState(false)

  const loadReport = async (cancelledRef?: { cancelled: boolean }) => {
    try {
      const value = await adminGet<ReductionReport>('/admin/overview/backlog-reduction/report', { timeoutMs: 8_000 })
      if (cancelledRef?.cancelled) return
      setReport(value)
    } catch (e) {
      if (cancelledRef?.cancelled) return
      setDetailsError((current) => [current, errorMessage(e)].filter(Boolean).join('\n'))
    }
  }

  const loadLatestFullSafeRun = async (cancelledRef?: { cancelled: boolean }) => {
    try {
      const value = await adminGet<FullSafeRun | null>(FULL_SAFE_RUN_LATEST_PATH, { timeoutMs: 8_000 })
      if (cancelledRef?.cancelled) return null
      const next = normalizeFullSafeRun(value)
      setFullSafeRun(next)
      return next
    } catch (e) {
      if (cancelledRef?.cancelled) return null
      setFullSafeRunError(errorMessage(e))
      return null
    }
  }

  const loadFullSafeRun = async (jobId: number) => {
    const value = await adminGet<FullSafeRun>(`${FULL_SAFE_RUN_PATH}/${jobId}`, { timeoutMs: 8_000 })
    const next = normalizeFullSafeRun(value)
    setFullSafeRun(next)
    return next
  }

  const loadDetails = async (cancelledRef?: { cancelled: boolean }) => {
    setDetailsLoading(true)
    setDetailsError(null)
    void loadReport(cancelledRef)
    void loadLatestFullSafeRun(cancelledRef)

    const [backlogResult, planResult] = await Promise.allSettled([
      adminGet<BacklogBreakdown>('/admin/overview/backlog-breakdown', { timeoutMs: 8_000 }),
      adminGet<ReductionPlan>('/admin/overview/backlog-reduction-plan', { timeoutMs: 8_000 }),
    ])
    if (cancelledRef?.cancelled) return

    const detailErrors: string[] = []
    if (backlogResult.status === 'fulfilled') {
      setBreakdown(backlogResult.value)
    } else {
      detailErrors.push(errorMessage(backlogResult.reason))
    }
    if (planResult.status === 'fulfilled') {
      const safePlan = {
        ...planResult.value,
        summary: planResult.value.summary ?? {},
        actions: Array.isArray(planResult.value.actions) ? planResult.value.actions : [],
      }
      setPlan(safePlan)
      setSelectedAction(safePlan.actions.find((action) => action.enabled)?.code ?? '')
    } else {
      detailErrors.push(errorMessage(planResult.reason))
    }
    setDetailsError(detailErrors.length ? detailErrors.join('\n') : null)
    setDetailsLoading(false)
  }

  useEffect(() => {
    const cancelledRef = { cancelled: false }

    const load = async () => {
      setLoading(true)
      setError(null)
      setDetailsError(null)
      setDetailsLoading(false)
      setBreakdown(null)
      setPlan(null)
      setReport(null)
      setFullSafeRun(null)
      setFullSafeRunError(null)

      try {
        const overview = await adminGet<Overview>('/admin/overview')
        if (cancelledRef.cancelled) return
        setData(overview)
        setLoading(false)
      } catch (e) {
        if (cancelledRef.cancelled) return
        setError(errorMessage(e))
        setLoading(false)
        return
      }

      if (cancelledRef.cancelled) return
      await loadDetails(cancelledRef)
    }

    void load()
    return () => {
      cancelledRef.cancelled = true
    }
  }, [])

  if (loading) return <AdminLoading />
  if (error) return <AdminError message={error} />
  if (!data) return null

  const renderSection = (title: string, cards: ActionCard[]) => (
    <section className="admin-section">
      <h3 className="admin-section-title">{title}</h3>
      <div className="admin-action-grid">
        {cards.map((c) => (
          <Link key={c.code} to={c.link_path} className={`admin-action-card ${severityClass(c.severity)}`} aria-label={`${c.title}: ${c.count}. ${actionLabel(c)}`}>
            <div className="admin-action-count">{c.count}</div>
            <div className="admin-action-title">{c.title}</div>
            {(c.short_hint || c.hint) && <div className="admin-action-hint" data-testid={`overview-card-hint-${c.code}`}>{c.short_hint || c.hint}</div>}
            <div className="admin-action-hint admin-action-card-action">{actionLabel(c)} →</div>
          </Link>
        ))}
      </div>
    </section>
  )
  const renderBacklog = () => {
    if (!breakdown) return null
    const topQueues = breakdown.queues
      .filter((queue) => ['manual_review', 'needs_verification', 'route_blockers', 'no_description', 'low_confidence'].includes(queue.code))
      .slice(0, 5)
    return (
      <section className="admin-section" data-testid="admin-backlog-breakdown">
        <h3 className="admin-section-title">Разбор очередей</h3>
        <div className="admin-action-grid">
          <div className="admin-action-card">
            <div className="admin-action-count">{breakdown.summary.unique_problem_places}</div>
            <div className="admin-action-title">Проблемных мест</div>
            <div className="admin-action-hint">Уникальные места, а не сумма всех сигналов.</div>
          </div>
          <div className="admin-action-card">
            <div className="admin-action-count">{breakdown.summary.total_problem_signals}</div>
            <div className="admin-action-title">Сигналов качества</div>
            <div className="admin-action-hint">Одно место может иметь несколько проблем.</div>
          </div>
          <div className="admin-action-card">
            <div className="admin-action-count">{breakdown.summary.auto_fixable_places}</div>
            <div className="admin-action-title">Можно автоматом</div>
            <div className="admin-action-hint">Кандидаты для автообработки и перепроверки.</div>
          </div>
          <div className="admin-action-card">
            <div className="admin-action-count">{breakdown.summary.manual_places}</div>
            <div className="admin-action-title">Нужен разбор</div>
            <div className="admin-action-hint">Очередь, которую нужно классифицировать.</div>
          </div>
        </div>
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Очередь</th><th>Всего</th><th>Авто</th><th>Разбор</th><th>Главные причины</th></tr></thead>
            <tbody>
              {topQueues.map((queue) => (
                <tr key={queue.code} data-testid={`backlog-queue-${queue.code}`}>
                  <td><strong>{queue.title}</strong><br /><span>{queue.recommended_action}</span></td>
                  <td>{queue.total_count}<br /><span>{queue.unique_places_count} мест</span></td>
                  <td>{queue.auto_fixable_count}</td>
                  <td>{queue.manual_count}</td>
                  <td>
                    {queue.reasons.filter((reason) => reason.count > 0).slice(0, 4).map((reason) => (
                      <div key={reason.code} data-testid={`backlog-reason-${reason.code}`}>{reason.title}: {reason.count}</div>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    )
  }
  const renderReport = () => {
    if (!report) return null
    const last = report.last_result
    return (
      <section className="admin-section" data-testid="admin-backlog-reduction-report">
        <h3 className="admin-section-title">Отчёт по снижению очередей</h3>
        <div className="admin-action-grid">
          <div className="admin-action-card">
            <div className="admin-action-count">{report.summary.queued_24h}</div>
            <div className="admin-action-title">Поставлено за 24 часа</div>
            <div className="admin-action-hint">Задачи, созданные для обработки данных.</div>
          </div>
          <div className="admin-action-card">
            <div className="admin-action-count">{report.summary.active_tasks}</div>
            <div className="admin-action-title">Активных задач</div>
            <div className="admin-action-hint">Задачи, которые ещё не завершены.</div>
          </div>
          <div className="admin-action-card">
            <div className="admin-action-count">{report.summary.skipped_24h}</div>
            <div className="admin-action-title">Пропущено за 24 часа</div>
            <div className="admin-action-hint">Обычно это уже поставленные задачи без дублей.</div>
          </div>
          <div className="admin-action-card">
            <div className="admin-action-count">{report.summary.failed_24h}</div>
            <div className="admin-action-title">Ошибок за 24 часа</div>
            <div className="admin-action-hint">Должно быть 0.</div>
          </div>
        </div>
        {last ? (
          <div className="admin-help-panel" data-testid="backlog-reduction-last-result">
            <strong>Последний запуск: #{last.job_id} · {actionTitle(last.action_code)} · {statusTitle(last.status)}</strong>
            <div>Когда: {formatDate(last.started_at)}. Запустил: {last.actor || '—'}.</div>
            <div>Кандидатов: {last.affected_count}. Изменено: {last.changed_count}. Поставлено: {last.queued_count}. Пропущено: {last.skipped_count}. Ошибок: {last.failed_count}.</div>
            {last.message && <div>{last.message}</div>}
          </div>
        ) : (
          <div className="admin-help-panel" data-testid="backlog-reduction-no-result">Запусков backlog reduction ещё не было.</div>
        )}
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Тип задачи</th><th>Всего создано</th><th>Активно</th><th>Статусы</th></tr></thead>
            <tbody>
              {report.task_stats.map((stat) => (
                <tr key={stat.task_type} data-testid={`backlog-task-stat-${stat.task_type}`}>
                  <td><strong>{actionTitle(stat.task_type)}</strong></td>
                  <td>{stat.total_count}</td>
                  <td>{stat.active_count}</td>
                  <td>{Object.entries(stat.statuses).map(([status, count]) => `${statusTitle(status)}: ${count}`).join(', ') || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Последние запуски</th><th>Действие</th><th>Поставлено</th><th>Пропущено</th><th>Ошибки</th></tr></thead>
            <tbody>
              {report.recent_runs.slice(0, 10).map((run) => (
                <tr key={run.job_id} data-testid={`backlog-run-${run.job_id}`}>
                  <td>#{run.job_id}<br /><span>{formatDate(run.started_at)}</span></td>
                  <td>{actionTitle(run.action_code)}</td>
                  <td>{run.queued_count}</td>
                  <td>{run.skipped_count}</td>
                  <td>{run.failed_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    )
  }
  const refreshFullSafeRun = async () => {
    setFullSafeRunRefreshing(true)
    setFullSafeRunError(null)
    try {
      if (fullSafeRun?.job_id) {
        await loadFullSafeRun(fullSafeRun.job_id)
      } else {
        await loadLatestFullSafeRun()
      }
    } catch (e) {
      setFullSafeRunError(errorMessage(e))
    } finally {
      setFullSafeRunRefreshing(false)
    }
  }
  const stopFullSafeRun = async () => {
    if (!fullSafeRun?.job_id) return
    setFullSafeRunStopping(true)
    setFullSafeRunError(null)
    try {
      const stopped = await adminPost<FullSafeRun>(`${FULL_SAFE_RUN_PATH}/${fullSafeRun.job_id}/stop`)
      setFullSafeRun(normalizeFullSafeRun(stopped))
    } catch (e) {
      setFullSafeRunError(errorMessage(e))
    } finally {
      setFullSafeRunStopping(false)
    }
  }
  const runFullSafeReduction = async () => {
    setFullSafeRunRunning(true)
    setFullSafeRunError(null)

    try {
      const created = normalizeFullSafeRun(await adminPostLong<FullSafeRun>(FULL_SAFE_RUN_PATH))
      if (!created) return
      setFullSafeRun(created)
      const jobId = created.job_id

      for (const actionCode of FULL_SAFE_REDUCTION_ACTIONS) {
        const current = await loadFullSafeRun(jobId)
        if (current?.stop_requested || current?.status === 'stopped') break

        const running = await adminPostLong<FullSafeRun>(`${FULL_SAFE_RUN_PATH}/${jobId}/steps/${actionCode}/running`)
        setFullSafeRun(normalizeFullSafeRun(running))

        try {
          const result = await adminPostLong<ReductionResult>(BACKLOG_REDUCTION_APPLY_PATH, {
            action_code: actionCode,
            confirmation_text: 'APPLY',
            limit: FULL_SAFE_REDUCTION_LIMIT,
            include_samples: true,
          })
          const recorded = await adminPostLong<FullSafeRun>(`${FULL_SAFE_RUN_PATH}/${jobId}/steps/${actionCode}/result`, result)
          setFullSafeRun(normalizeFullSafeRun(recorded))
        } catch (e) {
          const recorded = await adminPostLong<FullSafeRun>(`${FULL_SAFE_RUN_PATH}/${jobId}/steps/${actionCode}/error`, { message: errorMessage(e) })
          setFullSafeRun(normalizeFullSafeRun(recorded))
        }
      }

      const latestBeforeComplete = await loadFullSafeRun(jobId)
      if (!latestBeforeComplete?.stop_requested && latestBeforeComplete?.status !== 'stopped') {
        const completed = await adminPostLong<FullSafeRun>(`${FULL_SAFE_RUN_PATH}/${jobId}/complete`)
        setFullSafeRun(normalizeFullSafeRun(completed))
      }
      await loadReport()
      await loadLatestFullSafeRun()
    } catch (e) {
      setFullSafeRunError(errorMessage(e))
      await loadLatestFullSafeRun()
    } finally {
      setFullSafeRunRunning(false)
    }
  }
  const renderFullSafeReduction = () => {
    const run = fullSafeRun
    const canStop = Boolean(run?.job_id && run.is_running)
    const canStart = !fullSafeRunRunning && !(run?.is_running && !run.is_stale)
    return (
      <section className="admin-section" data-testid="admin-full-safe-backlog-run">
        <h3 className="admin-section-title">Полный безопасный прогон</h3>
        <div className="admin-help-panel">
          <div>Последовательно запускает безопасное пополнение очередей: фото, адреса, описания и перепроверку данных.</div>
          <div className="admin-filter-card">
            <button className="admin-btn admin-btn-primary" type="button" disabled={!canStart} onClick={() => void runFullSafeReduction()}>
              {fullSafeRunRunning ? 'Запускаем полный прогон…' : 'Запустить полный безопасный прогон'}
            </button>
            <button className="admin-btn admin-btn-secondary" type="button" disabled={fullSafeRunRefreshing} onClick={() => void refreshFullSafeRun()}>
              {fullSafeRunRefreshing ? 'Обновляем…' : 'Обновить статус'}
            </button>
            <button className="admin-btn admin-btn-secondary" type="button" disabled={!canStop || fullSafeRunStopping} onClick={() => void stopFullSafeRun()}>
              {fullSafeRunStopping ? 'Останавливаем…' : 'Остановить процесс'}
            </button>
          </div>
        </div>
        {fullSafeRunError && <div className="admin-state admin-state-error">{fullSafeRunError}</div>}
        {run ? (
          <div data-testid="full-safe-backlog-run-result">
            {(run.runtime_status === 'stuck' || run.is_stale) && <div className="admin-state admin-state-error">Нет прогресса больше 10 минут</div>}
            <div className="admin-help-panel" data-testid="full-safe-run-job">
              <strong>Процесс #{run.job_id}</strong>
              <div>Статус: {statusTitle(run.status)} / {statusTitle(run.runtime_status)}</div>
              <div>Начат: {formatDate(run.started_at)}. Последний прогресс: {formatDate(run.last_heartbeat_at)}.</div>
              <div>Кандидатов: {run.affected_count}. Изменено: {run.changed_count}. Поставлено: {run.queued_count}. Пропущено: {run.skipped_count}. Ошибок: {run.failed_count}. Осталось: {run.remaining_count}.</div>
            </div>
            <div className="admin-action-grid">
              <div className="admin-action-card">
                <div className="admin-action-count">{run.affected_count}</div>
                <div className="admin-action-title">Всего кандидатов</div>
              </div>
              <div className="admin-action-card">
                <div className="admin-action-count">{run.queued_count}</div>
                <div className="admin-action-title">Всего поставлено в очередь</div>
              </div>
              <div className="admin-action-card">
                <div className="admin-action-count">{run.skipped_count}</div>
                <div className="admin-action-title">Всего пропущено</div>
              </div>
              <div className="admin-action-card">
                <div className="admin-action-count">{run.failed_count}</div>
                <div className="admin-action-title">Всего ошибок</div>
              </div>
              <div className="admin-action-card">
                <div className="admin-action-count">{run.remaining_count}</div>
                <div className="admin-action-title">Осталось шагов</div>
              </div>
            </div>
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead><tr><th>Действие</th><th>Статус</th><th>Кандидаты</th><th>Поставлено</th><th>Пропущено</th><th>Ошибки</th></tr></thead>
                <tbody>
                  {run.actions.map((step) => (
                    <tr key={step.action_code} data-testid={`full-safe-run-${step.action_code}`}>
                      <td><strong>{actionTitle(step.action_code, step.title)}</strong></td>
                      <td>{statusTitle(step.status)}</td>
                      <td>{step.affected_count}</td>
                      <td>{step.queued_count}</td>
                      <td>{step.skipped_count}</td>
                      <td>{step.failed_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="admin-help-panel" data-testid="full-safe-backlog-run-empty">Полных прогонов пока не было.</div>
        )}
      </section>
    )
  }
  const selected = plan?.actions.find((action) => action.code === selectedAction)
  const runReduction = async (mode: 'dry-run' | 'apply') => {
    if (!selected) return
    setRunningAction(mode)
    setReductionError(null)
    try {
      const body = {
        action_code: selected.code,
        limit: Math.min(limit, selected.max_batch_size),
        ...(mode === 'apply' ? { confirmation_text: confirmation } : {}),
      }
      const path = mode === 'apply' ? BACKLOG_REDUCTION_APPLY_PATH : '/admin/overview/backlog-reduction/dry-run'
      setReductionResult(await adminPost<ReductionResult>(path, body))
      void loadReport()
    } catch (e) {
      setReductionError(e instanceof Error ? e.message : 'Не удалось выполнить действие')
    } finally {
      setRunningAction(null)
    }
  }
  const renderReduction = () => {
    if (!plan) return null
    return (
      <section className="admin-section" data-testid="admin-backlog-reduction">
        <h3 className="admin-section-title">План уменьшения очередей</h3>
        <div className="admin-action-grid">
          <div className="admin-action-card">
            <div className="admin-action-count">{plan.summary.total_auto_fixable ?? 0}</div>
            <div className="admin-action-title">Можно обработать автоматически</div>
            <div className="admin-action-hint">Доступно через пробный запуск и подтверждение.</div>
          </div>
          <div className="admin-action-card">
            <div className="admin-action-count">{plan.summary.manual_review_reclassifiable ?? 0}</div>
            <div className="admin-action-title">Можно убрать из ручного разбора</div>
            <div className="admin-action-hint">Только очевидные случаи без публикации.</div>
          </div>
          <div className="admin-action-card">
            <div className="admin-action-count">{plan.summary.content_enrichment_queueable ?? 0}</div>
            <div className="admin-action-title">Можно поставить в обработку</div>
            <div className="admin-action-hint">Без выдуманных фото, адресов и описаний.</div>
          </div>
        </div>
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Действие</th><th>Кандидаты</th><th>Что изменится</th><th>Статус</th></tr></thead>
            <tbody>
              {plan.actions.map((action) => (
                <tr key={action.code}>
                  <td><label><input type="radio" checked={selectedAction === action.code} disabled={!action.enabled} onChange={() => setSelectedAction(action.code)} /> <strong>{action.title}</strong></label><br /><span>{action.description}</span></td>
                  <td>{action.affected_count}</td>
                  <td>{action.expected_effect}</td>
                  <td>{action.enabled ? 'Готово к пробному запуску' : action.disabled_reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="admin-filter-card">
          <label className="admin-field">Лимит за запуск<input type="number" min={1} max={selected?.max_batch_size ?? 100} value={limit} onChange={(e) => setLimit(Number(e.target.value) || 1)} /></label>
          <button className="admin-btn admin-btn-secondary" type="button" disabled={!selected || runningAction !== null || fullSafeRunRunning} onClick={() => void runReduction('dry-run')}>{runningAction === 'dry-run' ? 'Проверяем...' : 'Пробный запуск'}</button>
          <label className="admin-field">Подтверждение<input value={confirmation} onChange={(e) => setConfirmation(e.target.value)} placeholder="Введите APPLY" /></label>
          <button className="admin-btn admin-btn-primary" type="button" disabled={!selected || !reductionResult?.dry_run || confirmation !== 'APPLY' || runningAction !== null || fullSafeRunRunning} onClick={() => void runReduction('apply')}>{runningAction === 'apply' ? 'Применяем...' : 'Применить безопасно'}</button>
        </div>
        {reductionError && <div className="admin-state admin-state-error">{reductionError}</div>}
        {reductionResult && (
          <div className="admin-help-panel" data-testid="reduction-result">
            <strong>{reductionResult.message}</strong>
            <div>
              Кандидатов: {reductionResult.affected_count}. {reductionResult.dry_run ? `Изменится: ${reductionResult.would_change_count ?? reductionResult.changed_count}.` : `Изменено: ${reductionResult.changed_count}.`} Поставлено в обработку: {reductionResult.queued_count}. Пропущено: {reductionResult.skipped_count}. Ошибок: {reductionResult.failed_count}.
            </div>
          </div>
        )}
      </section>
    )
  }

  return (
    <div>
      <h2 className="admin-page-title">Обзор</h2>
      <p className="admin-page-subtitle">Что сейчас требует внимания. Карточки разделяют автоочередь, ручную проверку и блокеры маршрутов.</p>
      {renderSection('Критические задачи', data.critical)}
      {renderSection('Качество данных', data.data_quality)}
      {renderFullSafeReduction()}
      {renderReport()}
      {detailsLoading && <AdminLoading message="Загружаем детали очередей…" />}
      {detailsError && <AdminSectionError title="Часть данных обзора не загрузилась" message={detailsError} />}
      {renderBacklog()}
      {renderReduction()}
      {renderSection('Операции', data.operations)}
      <Link className="admin-btn admin-btn-sm" to="/admin/audit">Событий в журнале аудита: {data.recent_audit_count} →</Link>
    </div>
  )
}
