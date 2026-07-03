import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminGet } from './adminApi'
import { AdminError, AdminLoading } from './shared/AdminStates'

type ActionCard = { code: string; title: string; count: number; severity: string; link_path: string; hint?: string | null; action_label?: string | null }
type Overview = { critical: ActionCard[]; data_quality: ActionCard[]; operations: ActionCard[]; recent_audit_count: number }

const severityClass = (s: string) => `admin-severity admin-severity-${s}`
const actionLabel = (card: ActionCard) => card.action_label || 'Открыть выборку'

export const AdminOverviewPage = () => {
  const [data, setData] = useState<Overview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    adminGet<Overview>('/admin/overview')
      .then(setData)
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
            {c.hint && <div className="admin-action-hint">{c.hint}</div>}
            <div className="admin-action-hint">{actionLabel(c)} →</div>
          </Link>
        ))}
      </div>
    </section>
  )

  return (
    <div>
      <h2 className="admin-page-title">Обзор</h2>
      <p className="admin-page-subtitle">Что сейчас требует внимания. Карточки разделяют автоочередь, ручную проверку и блокеры маршрутов.</p>
      {renderSection('Критические задачи', data.critical)}
      {renderSection('Качество данных', data.data_quality)}
      {renderSection('Операции', data.operations)}
      <Link className="admin-btn admin-btn-sm" to="/admin/audit">Событий в журнале аудита: {data.recent_audit_count} →</Link>
    </div>
  )
}
