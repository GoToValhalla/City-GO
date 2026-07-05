import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import { AdminError, AdminLoading, AdminSectionError } from './shared/AdminStates'

type ActionCard = { code: string; title: string; count: number; severity: string; link_path: string; hint?: string | null; action_label?: string | null; short_hint?: string | null }
type Overview = { critical: ActionCard[]; data_quality: ActionCard[]; operations: ActionCard[]; recent_audit_count: number }
type BacklogReason = { code: string; title: string; count: number }
type BacklogQueue = { code: string; title: string; total_count: number; unique_places_count: number; auto_fixable_count: number; manual_count: number; recommended_action: string; reasons: BacklogReason[] }
type BacklogBreakdown = { summary: Record<string, number>; queues: BacklogQueue[] }
type ReductionAction = { code: string; title: string; description: string; expected_effect: string; enabled: boolean; disabled_reason?: string | null; affected_count: number; max_batch_size: number }
type ReductionPlan = { summary: Record<string, number>; actions: ReductionAction[] }
type ReductionResult = { action_code: string; status: string; dry_run: boolean; affected_count: number; would_change_count?: number; changed_count: number; skipped_count: number; failed_count: number; queued_count: number; message: string }
type ReductionReport = { summary: Record<string, number>; last_result: { job_id: number; status: string; action_code?: string | null; affected_count: number; changed_count: number; queued_count: number; skipped_count: number; failed_count: number } | null; task_stats: { task_type: string; total_count: number; active_count: number; statuses: Record<string, number> }[]; recent_runs: unknown[] }
type FullSafeRunStep = { action_code: string; title?: string | null; status: string; affected_count: number; queued_count: number; skipped_count: number; failed_count: number }
type FullSafeRun = { job_id: number; status: string; runtime_status: string; is_running: boolean; is_stale: boolean; started_at?: string | null; last_heartbeat_at?: string | null; affected_count: number; changed_count: number; queued_count: number; skipped_count: number; failed_count: number; remaining_count: number; stop_requested: boolean; actions: FullSafeRunStep[] }

const APPLY_PATH = '/admin/overview/backlog-reduction/apply'
const FULL_RUN_PATH = '/admin/overview/backlog-reduction/full-safe-run'
const FULL_RUN_START_PATH = `${FULL_RUN_PATH}/start`
const FULL_RUN_LATEST_PATH = `${FULL_RUN_PATH}/latest`
const ACTION_TITLES: Record<string, string> = {
  enqueue_photo_discovery: 'Фото', enqueue_address_recovery: 'Адреса', enqueue_description_enrichment: 'Описания', auto_recheck_verification_backlog: 'Перепроверка данных',
  recompute_route_eligibility: 'Проверка маршрутов', exclude_service_places_from_routes: 'Служебные места', classify_unknown_categories_deterministic: 'Категории', normalize_manual_review_backlog: 'Ручной разбор', recompute_low_confidence: 'Низкая уверенность',
}
const STATUS_TITLES: Record<string, string> = { pending: 'Ожидает', running: 'В работе', queued: 'В очереди', processing: 'Обрабатывается', locked: 'Занято', stop_requested: 'Остановка запрошена', stopped: 'Остановлен', stuck: 'Нет прогресса', applied: 'Готово', completed: 'Готово', partial: 'Частично', failed: 'Ошибка', unsupported: 'Не поддержано' }

const actionLabel = (card: ActionCard) => card.action_label || 'Открыть выборку'
const severityClass = (value: string) => `admin-severity admin-severity-${value}`
const errorMessage = (error: unknown) => (error instanceof Error ? error.message : 'Не удалось загрузить данные')
const actionTitle = (code?: string | null, fallback?: string | null) => fallback || ACTION_TITLES[code ?? ''] || 'Действие'
const statusTitle = (status?: string | null) => STATUS_TITLES[status ?? ''] ?? 'Неизвестно'
const formatDate = (value?: string | null) => {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('ru-RU')
}
const normalizeRun = (run: FullSafeRun | null): FullSafeRun | null => {
  if (!run?.job_id) return null
  return { ...run, actions: Array.isArray(run.actions) ? run.actions : [], affected_count: Number(run.affected_count || 0), changed_count: Number(run.changed_count || 0), queued_count: Number(run.queued_count || 0), skipped_count: Number(run.skipped_count || 0), failed_count: Number(run.failed_count || 0), remaining_count: Number(run.remaining_count || 0) }
}

export const AdminOverviewPage = () => {
  const [data, setData] = useState<Overview | null>(null)
  const [breakdown, setBreakdown] = useState<BacklogBreakdown | null>(null)
  const [plan, setPlan] = useState<ReductionPlan | null>(null)
  const [report, setReport] = useState<ReductionReport | null>(null)
  const [selectedAction, setSelectedAction] = useState('')
  const [limit, setLimit] = useState(100)
  const [confirmation, setConfirmation] = useState('')
  const [runningAction, setRunningAction] = useState<string | null>(null)
  const [reductionResult, setReductionResult] = useState<ReductionResult | null>(null)
  const [reductionError, setReductionError] = useState<string | null>(null)
  const [fullRun, setFullRun] = useState<FullSafeRun | null>(null)
  const [fullRunBusy, setFullRunBusy] = useState(false)
  const [fullRunRefreshing, setFullRunRefreshing] = useState(false)
  const [fullRunStopping, setFullRunStopping] = useState(false)
  const [fullRunError, setFullRunError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const [detailsError, setDetailsError] = useState<string | null>(null)

  const loadReport = async () => setReport(await adminGet<ReductionReport>('/admin/overview/backlog-reduction/report', { timeoutMs: 8_000 }))
  const loadLatestFullRun = async () => {
    const run = normalizeRun(await adminGet<FullSafeRun | null>(FULL_RUN_LATEST_PATH, { timeoutMs: 8_000 }))
    setFullRun(run)
    return run
  }
  const loadFullRun = async (jobId: number) => {
    const run = normalizeRun(await adminGet<FullSafeRun>(`${FULL_RUN_PATH}/${jobId}`, { timeoutMs: 8_000 }))
    setFullRun(run)
    return run
  }

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        setLoading(true); setError(null); setDetailsError(null)
        const overview = await adminGet<Overview>('/admin/overview')
        if (cancelled) return
        setData(overview); setLoading(false); setDetailsLoading(true)
        const [reportResult, latestRunResult, backlogResult, planResult] = await Promise.allSettled([
          adminGet<ReductionReport>('/admin/overview/backlog-reduction/report', { timeoutMs: 8_000 }),
          adminGet<FullSafeRun | null>(FULL_RUN_LATEST_PATH, { timeoutMs: 8_000 }),
          adminGet<BacklogBreakdown>('/admin/overview/backlog-breakdown', { timeoutMs: 8_000 }),
          adminGet<ReductionPlan>('/admin/overview/backlog-reduction-plan', { timeoutMs: 8_000 }),
        ])
        if (cancelled) return
        const errors: string[] = []
        if (reportResult.status === 'fulfilled') setReport(reportResult.value); else errors.push(errorMessage(reportResult.reason))
        if (latestRunResult.status === 'fulfilled') setFullRun(normalizeRun(latestRunResult.value)); else setFullRunError(errorMessage(latestRunResult.reason))
        if (backlogResult.status === 'fulfilled') setBreakdown(backlogResult.value); else errors.push(errorMessage(backlogResult.reason))
        if (planResult.status === 'fulfilled') { setPlan(planResult.value); setSelectedAction((planResult.value.actions || []).find((action) => action.enabled)?.code ?? '') } else errors.push(errorMessage(planResult.reason))
        setDetailsError(errors.length ? errors.join('\n') : null)
        setDetailsLoading(false)
      } catch (e) {
        if (!cancelled) { setError(errorMessage(e)); setLoading(false) }
      }
    }
    void load()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (!fullRun?.job_id || !fullRun.is_running || fullRun.is_stale) return undefined
    const timer = window.setInterval(() => { void loadFullRun(fullRun.job_id) }, 5_000)
    return () => window.clearInterval(timer)
  }, [fullRun?.job_id, fullRun?.is_running, fullRun?.is_stale])

  if (loading) return <AdminLoading />
  if (error) return <AdminError message={error} />
  if (!data) return null

  const renderSection = (title: string, cards: ActionCard[]) => <section className="admin-section"><h3 className="admin-section-title">{title}</h3><div className="admin-action-grid">{cards.map((card) => <Link key={card.code} to={card.link_path} className={`admin-action-card ${severityClass(card.severity)}`} aria-label={`${card.title}: ${card.count}. ${actionLabel(card)}`}><div className="admin-action-count">{card.count}</div><div className="admin-action-title">{card.title}</div>{(card.short_hint || card.hint) && <div className="admin-action-hint" data-testid={`overview-card-hint-${card.code}`}>{card.short_hint || card.hint}</div>}<div className="admin-action-hint admin-action-card-action">{actionLabel(card)} →</div></Link>)}</div></section>

  const renderBacklog = () => breakdown ? <section className="admin-section" data-testid="admin-backlog-breakdown"><h3 className="admin-section-title">Разбор очередей</h3><div className="admin-action-grid"><div className="admin-action-card"><div className="admin-action-count">{breakdown.summary.unique_problem_places}</div><div className="admin-action-title">Проблемных мест</div></div><div className="admin-action-card"><div className="admin-action-count">{breakdown.summary.total_problem_signals}</div><div className="admin-action-title">Сигналов качества</div></div><div className="admin-action-card"><div className="admin-action-count">{breakdown.summary.auto_fixable_places}</div><div className="admin-action-title">Можно автоматом</div></div><div className="admin-action-card"><div className="admin-action-count">{breakdown.summary.manual_places}</div><div className="admin-action-title">Нужен разбор</div></div></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Очередь</th><th>Всего</th><th>Авто</th><th>Разбор</th><th>Главные причины</th></tr></thead><tbody>{breakdown.queues.filter((queue) => ['manual_review', 'needs_verification', 'route_blockers', 'no_description', 'low_confidence'].includes(queue.code)).slice(0, 5).map((queue) => <tr key={queue.code} data-testid={`backlog-queue-${queue.code}`}><td><strong>{queue.title}</strong><br /><span>{queue.recommended_action}</span></td><td>{queue.total_count}<br /><span>{queue.unique_places_count} мест</span></td><td>{queue.auto_fixable_count}</td><td>{queue.manual_count}</td><td>{queue.reasons.filter((reason) => reason.count > 0).slice(0, 4).map((reason) => <div key={reason.code}>{reason.title}: {reason.count}</div>)}</td></tr>)}</tbody></table></div></section> : null

  const renderReport = () => report ? <section className="admin-section" data-testid="admin-backlog-reduction-report"><h3 className="admin-section-title">Отчёт по снижению очередей</h3><div className="admin-action-grid"><div className="admin-action-card"><div className="admin-action-count">{report.summary.queued_24h || 0}</div><div className="admin-action-title">Поставлено за 24 часа</div></div><div className="admin-action-card"><div className="admin-action-count">{report.summary.active_tasks || 0}</div><div className="admin-action-title">Активных задач</div></div><div className="admin-action-card"><div className="admin-action-count">{report.summary.skipped_24h || 0}</div><div className="admin-action-title">Пропущено за 24 часа</div></div><div className="admin-action-card"><div className="admin-action-count">{report.summary.failed_24h || 0}</div><div className="admin-action-title">Ошибок за 24 часа</div></div></div>{report.last_result ? <div className="admin-help-panel" data-testid="backlog-reduction-last-result">Последний запуск: #{report.last_result.job_id}</div> : <div className="admin-help-panel" data-testid="backlog-reduction-no-result">Запусков снижения очередей ещё не было.</div>}</section> : null

  const startFullRun = async () => { setFullRunBusy(true); setFullRunError(null); try { setFullRun(normalizeRun(await adminPost<FullSafeRun>(FULL_RUN_START_PATH))); void loadReport() } catch (e) { setFullRunError(errorMessage(e)); await loadLatestFullRun().catch(() => undefined) } finally { setFullRunBusy(false) } }
  const refreshFullRun = async () => { setFullRunRefreshing(true); setFullRunError(null); try { if (fullRun?.job_id) await loadFullRun(fullRun.job_id); else await loadLatestFullRun() } catch (e) { setFullRunError(errorMessage(e)) } finally { setFullRunRefreshing(false) } }
  const stopFullRun = async () => { if (!fullRun?.job_id) return; setFullRunStopping(true); setFullRunError(null); try { setFullRun(normalizeRun(await adminPost<FullSafeRun>(`${FULL_RUN_PATH}/${fullRun.job_id}/stop`))) } catch (e) { setFullRunError(errorMessage(e)) } finally { setFullRunStopping(false) } }

  const renderFullRun = () => <section className="admin-section" data-testid="admin-full-safe-backlog-run"><h3 className="admin-section-title">Полный безопасный прогон</h3><div className="admin-help-panel"><div>Запускает на сервере безопасное пополнение очередей: фото, адреса, описания и перепроверку данных.</div><div className="admin-filter-card"><button className="admin-btn admin-btn-primary" type="button" disabled={fullRunBusy || Boolean(fullRun?.is_running && !fullRun.is_stale)} onClick={() => void startFullRun()}>{fullRunBusy ? 'Запускаем полный прогон…' : 'Запустить полный безопасный прогон'}</button><button className="admin-btn admin-btn-secondary" type="button" disabled={fullRunRefreshing} onClick={() => void refreshFullRun()}>{fullRunRefreshing ? 'Обновляем…' : 'Обновить статус'}</button><button className="admin-btn admin-btn-secondary" type="button" disabled={!fullRun?.is_running || fullRunStopping} onClick={() => void stopFullRun()}>{fullRunStopping ? 'Останавливаем…' : 'Остановить процесс'}</button></div></div>{fullRunError && <div className="admin-state admin-state-error">{fullRunError}</div>}{fullRun ? <div data-testid="full-safe-backlog-run-result">{(fullRun.runtime_status === 'stuck' || fullRun.is_stale) && <div className="admin-state admin-state-error">Нет прогресса больше 10 минут</div>}<div className="admin-help-panel" data-testid="full-safe-run-job"><strong>Процесс #{fullRun.job_id}</strong><div>Статус: {statusTitle(fullRun.status)} / {statusTitle(fullRun.runtime_status)}</div><div>Начат: {formatDate(fullRun.started_at)}. Последний прогресс: {formatDate(fullRun.last_heartbeat_at)}.</div><div>Кандидатов: {fullRun.affected_count}. Изменено: {fullRun.changed_count}. Поставлено: {fullRun.queued_count}. Пропущено: {fullRun.skipped_count}. Ошибок: {fullRun.failed_count}. Осталось: {fullRun.remaining_count}.</div></div><div className="admin-action-grid"><div className="admin-action-card"><div className="admin-action-count">{fullRun.affected_count}</div><div className="admin-action-title">Всего кандидатов</div></div><div className="admin-action-card"><div className="admin-action-count">{fullRun.queued_count}</div><div className="admin-action-title">Всего поставлено в очередь</div></div><div className="admin-action-card"><div className="admin-action-count">{fullRun.skipped_count}</div><div className="admin-action-title">Всего пропущено</div></div><div className="admin-action-card"><div className="admin-action-count">{fullRun.failed_count}</div><div className="admin-action-title">Всего ошибок</div></div><div className="admin-action-card"><div className="admin-action-count">{fullRun.remaining_count}</div><div className="admin-action-title">Осталось шагов</div></div></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Действие</th><th>Статус</th><th>Кандидаты</th><th>Поставлено</th><th>Пропущено</th><th>Ошибки</th></tr></thead><tbody>{fullRun.actions.map((step) => <tr key={step.action_code} data-testid={`full-safe-run-${step.action_code}`}><td><strong>{actionTitle(step.action_code, step.title)}</strong></td><td>{statusTitle(step.status)}</td><td>{step.affected_count}</td><td>{step.queued_count}</td><td>{step.skipped_count}</td><td>{step.failed_count}</td></tr>)}</tbody></table></div></div> : <div className="admin-help-panel" data-testid="full-safe-backlog-run-empty">Полных прогонов пока не было.</div>}</section>

  const selected = plan?.actions.find((action) => action.code === selectedAction)
  const runReduction = async (mode: 'dry-run' | 'apply') => { if (!selected) return; setRunningAction(mode); setReductionError(null); try { const body = { action_code: selected.code, limit: Math.min(limit, selected.max_batch_size), ...(mode === 'apply' ? { confirmation_text: confirmation } : {}) }; setReductionResult(await adminPost<ReductionResult>(mode === 'apply' ? APPLY_PATH : '/admin/overview/backlog-reduction/dry-run', body)); void loadReport() } catch (e) { setReductionError(errorMessage(e)) } finally { setRunningAction(null) } }
  const renderReduction = () => plan ? <section className="admin-section" data-testid="admin-backlog-reduction"><h3 className="admin-section-title">План уменьшения очередей</h3><div className="admin-action-grid"><div className="admin-action-card"><div className="admin-action-count">{plan.summary.total_auto_fixable ?? 0}</div><div className="admin-action-title">Можно обработать автоматически</div></div><div className="admin-action-card"><div className="admin-action-count">{plan.summary.manual_review_reclassifiable ?? 0}</div><div className="admin-action-title">Можно убрать из ручного разбора</div></div><div className="admin-action-card"><div className="admin-action-count">{plan.summary.content_enrichment_queueable ?? 0}</div><div className="admin-action-title">Можно поставить в обработку</div></div></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Действие</th><th>Кандидаты</th><th>Что изменится</th><th>Статус</th></tr></thead><tbody>{plan.actions.map((action) => <tr key={action.code}><td><label><input type="radio" checked={selectedAction === action.code} disabled={!action.enabled} onChange={() => setSelectedAction(action.code)} /> <strong>{action.title}</strong></label><br /><span>{action.description}</span></td><td>{action.affected_count}</td><td>{action.expected_effect}</td><td>{action.enabled ? 'Готово к пробному запуску' : action.disabled_reason}</td></tr>)}</tbody></table></div><div className="admin-filter-card"><label className="admin-field">Лимит за запуск<input type="number" min={1} max={selected?.max_batch_size ?? 100} value={limit} onChange={(e) => setLimit(Number(e.target.value) || 1)} /></label><button className="admin-btn admin-btn-secondary" type="button" disabled={!selected || runningAction !== null || fullRunBusy || Boolean(fullRun?.is_running && !fullRun.is_stale)} onClick={() => void runReduction('dry-run')}>{runningAction === 'dry-run' ? 'Проверяем...' : 'Пробный запуск'}</button><label className="admin-field">Подтверждение<input value={confirmation} onChange={(e) => setConfirmation(e.target.value)} placeholder="Введите APPLY" /></label><button className="admin-btn admin-btn-primary" type="button" disabled={!selected || !reductionResult?.dry_run || confirmation !== 'APPLY' || runningAction !== null || fullRunBusy || Boolean(fullRun?.is_running && !fullRun.is_stale)} onClick={() => void runReduction('apply')}>{runningAction === 'apply' ? 'Применяем...' : 'Применить безопасно'}</button></div>{reductionError && <div className="admin-state admin-state-error">{reductionError}</div>}{reductionResult && <div className="admin-help-panel" data-testid="reduction-result"><strong>{reductionResult.message}</strong><div>Кандидатов: {reductionResult.affected_count}. {reductionResult.dry_run ? `Изменится: ${reductionResult.would_change_count ?? reductionResult.changed_count}.` : `Изменено: ${reductionResult.changed_count}.`} Поставлено в обработку: {reductionResult.queued_count}. Пропущено: {reductionResult.skipped_count}. Ошибок: {reductionResult.failed_count}.</div></div>}</section> : null

  return <div><h2 className="admin-page-title">Обзор</h2><p className="admin-page-subtitle">Что сейчас требует внимания. Карточки разделяют автоочередь, ручную проверку и блокеры маршрутов.</p>{renderSection('Критические задачи', data.critical)}{renderSection('Качество данных', data.data_quality)}{renderFullRun()}{renderReport()}{detailsLoading && <AdminLoading message="Загружаем детали очередей…" />}{detailsError && <AdminSectionError title="Часть данных обзора не загрузилась" message={detailsError} />}{renderBacklog()}{renderReduction()}{renderSection('Операции', data.operations)}<Link className="admin-btn admin-btn-sm" to="/admin/audit">Событий в журнале аудита: {data.recent_audit_count} →</Link></div>
}
