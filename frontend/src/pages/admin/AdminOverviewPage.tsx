import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminGet } from './adminApi'
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

const severityClass = (s: string) => `admin-severity admin-severity-${s}`
const actionLabel = (card: ActionCard) => card.action_label || 'Открыть выборку'

export const AdminOverviewPage = () => {
  const [data, setData] = useState<Overview | null>(null)
  const [breakdown, setBreakdown] = useState<BacklogBreakdown | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      adminGet<Overview>('/admin/overview'),
      adminGet<BacklogBreakdown>('/admin/overview/backlog-breakdown'),
    ])
      .then(([overview, backlog]) => { setData(overview); setBreakdown(backlog) })
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

  return (
    <div>
      <h2 className="admin-page-title">Обзор</h2>
      <p className="admin-page-subtitle">Что сейчас требует внимания. Карточки разделяют автоочередь, ручную проверку и блокеры маршрутов.</p>
      {renderSection('Критические задачи', data.critical)}
      {renderSection('Качество данных', data.data_quality)}
      {renderBacklog()}
      {renderSection('Операции', data.operations)}
      <Link className="admin-btn admin-btn-sm" to="/admin/audit">Событий в журнале аудита: {data.recent_audit_count} →</Link>
    </div>
  )
}
