import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminGet } from './adminApi'

type Summary = { needs_recheck?: number; verified_today?: number; unverified?: number; low_confidence?: number }
type QueueItem = { place_id: number; title: string; city_slug?: string; category?: string; address?: string | null; verification_status?: string; existence_confidence_score?: number }
type Queue = { items: QueueItem[]; total: number }
type Cities = { items: unknown[] }

const errorText = (error: unknown) => error instanceof Error ? error.message : 'Не удалось загрузить данные'

export const AdminPlaceVerificationsPage = () => {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [queue, setQueue] = useState<Queue>({ items: [], total: 0 })
  const [summaryError, setSummaryError] = useState('')
  const [queueError, setQueueError] = useState('')
  const [citiesError, setCitiesError] = useState('')

  useEffect(() => {
    let alive = true
    Promise.resolve().then(async () => {
      const [summaryResult, queueResult, citiesResult] = await Promise.allSettled([
        adminGet<Summary>('/admin/place-verifications/summary', { cache: false, timeoutMs: 8000 }),
        adminGet<Queue>('/admin/place-verifications/queue?limit=50&offset=0&status=needs_recheck', { cache: false, timeoutMs: 8000 }),
        adminGet<Cities>('/admin/cities?limit=100', { cache: false, timeoutMs: 8000 }),
      ])
      if (!alive) return
      if (summaryResult.status === 'fulfilled') setSummary(summaryResult.value); else setSummaryError(errorText(summaryResult.reason))
      if (queueResult.status === 'fulfilled') setQueue(queueResult.value); else setQueueError(errorText(queueResult.reason))
      if (citiesResult.status === 'rejected') setCitiesError(errorText(citiesResult.reason))
    })
    return () => { alive = false }
  }, [])

  return <div>
    <h2 className="admin-page-title">Проверка мест ({queue.total})</h2>
    <p className="admin-page-subtitle">Ручная очередь перепроверки мест.</p>
    {summaryError ? <p className="admin-error-text">{summaryError}</p> : null}
    {queueError ? <p className="admin-error-text">{queueError}</p> : null}
    {citiesError ? <p className="admin-error-text">{citiesError}</p> : null}
    {summary ? <section className="admin-metrics-grid admin-metrics-small">
      <div className="admin-metric-card"><div className="admin-metric-value">{summary.needs_recheck ?? 0}</div><div className="admin-metric-label">В очереди</div></div>
      <div className="admin-metric-card"><div className="admin-metric-value">{summary.verified_today ?? 0}</div><div className="admin-metric-label">Проверено сегодня</div></div>
      <div className="admin-metric-card"><div className="admin-metric-value">{summary.unverified ?? 0}</div><div className="admin-metric-label">Не проверено авто</div></div>
      <div className="admin-metric-card"><div className="admin-metric-value">{summary.low_confidence ?? 0}</div><div className="admin-metric-label">Низкая уверенность</div></div>
    </section> : null}
    <section className="admin-section">
      {queue.items.length ? <table className="admin-table"><tbody>{queue.items.map((item) => <tr key={item.place_id}><td><Link to={`/admin/places/${item.place_id}`}>{item.title}</Link></td><td>{item.city_slug}</td><td>{item.category}</td><td>{item.address ?? '—'}</td></tr>)}</tbody></table> : null}
    </section>
  </div>
}
