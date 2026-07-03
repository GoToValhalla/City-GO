import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import { AdminError, AdminLoading } from './shared/AdminStates'

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
  changed_count: number
  skipped_count: number
  failed_count: number
  queued_count: number
  message: string
}

const severityClass = (s: string) => `admin-severity admin-severity-${s}`
const actionLabel = (card: ActionCard) => card.action_label || 'Открыть выборку'

export const AdminOverviewPage = () => {
  const [data, setData] = useState<Overview | null>(null)
  const [breakdown, setBreakdown] = useState<BacklogBreakdown | null>(null)
  const [plan, setPlan] = useState<ReductionPlan | null>(null)
  const [selectedAction, setSelectedAction] = useState<string>('')
  const [limit, setLimit] = useState(100)
  const [confirmation, setConfirmation] = useState('')
  const [runningAction, setRunningAction] = useState<string | null>(null)
  const [reductionResult, setReductionResult] = useState<ReductionResult | null>(null)
  const [reductionError, setReductionError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      adminGet<Overview>('/admin/overview'),
      adminGet<BacklogBreakdown>('/admin/overview/backlog-breakdown'),
      adminGet<ReductionPlan>('/admin/overview/backlog-reduction-plan'),
    ])
      .then(([overview, backlog, reductionPlan]) => {
        const safePlan = {
          ...reductionPlan,
          summary: reductionPlan.summary ?? {},
          actions: Array.isArray(reductionPlan.actions) ? reductionPlan.actions : [],
        }
        setData(overview)
        setBreakdown(backlog)
        setPlan(safePlan)
        setSelectedAction(safePlan.actions.find((action) => action.enabled)?.code ?? '')
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
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
      const path = mode === 'apply' ? '/admin/overview/backlog-reduction/apply' : '/admin/overview/backlog-reduction/dry-run'
      setReductionResult(await adminPost<ReductionResult>(path, body))
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
          <button className="admin-btn admin-btn-secondary" type="button" disabled={!selected || runningAction !== null} onClick={() => void runReduction('dry-run')}>{runningAction === 'dry-run' ? 'Проверяем...' : 'Пробный запуск'}</button>
          <label className="admin-field">Подтверждение<input value={confirmation} onChange={(e) => setConfirmation(e.target.value)} placeholder="Введите APPLY" /></label>
          <button className="admin-btn admin-btn-primary" type="button" disabled={!selected || !reductionResult?.dry_run || confirmation !== 'APPLY' || runningAction !== null} onClick={() => void runReduction('apply')}>{runningAction === 'apply' ? 'Применяем...' : 'Применить безопасно'}</button>
        </div>
        {reductionError && <div className="admin-state admin-state-error">{reductionError}</div>}
        {reductionResult && (
          <div className="admin-help-panel" data-testid="reduction-result">
            <strong>{reductionResult.message}</strong>
            <div>Кандидатов: {reductionResult.affected_count}. Изменено: {reductionResult.changed_count}. Поставлено в обработку: {reductionResult.queued_count}. Пропущено: {reductionResult.skipped_count}. Ошибок: {reductionResult.failed_count}.</div>
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
      {renderBacklog()}
      {renderReduction()}
      {renderSection('Операции', data.operations)}
      <Link className="admin-btn admin-btn-sm" to="/admin/audit">Событий в журнале аудита: {data.recent_audit_count} →</Link>
    </div>
  )
}
