import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

type Row = { id: number; city_slug: string | null; name: string; expected_category: string; expected_scope: string; expected_route_policy: string; status: string; gap_reason?: string | null; matched_place_id?: number | null; matched_place_title?: string | null }
type Payload = { items: Row[]; summary: { total: number; matched: number; unresolved: number; critical_unresolved: number } }

export const AdminCoverageGapsPage = () => {
  const [data, setData] = useState<Payload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const load = () => {
    setLoading(true)
    adminGet<Payload>('/admin/coverage-gaps?limit=300').then(setData).catch((err: Error) => setError(err.message)).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const refresh = async () => {
    setRefreshing(true)
    try { await adminPost('/admin/coverage-gaps/refresh'); load() }
    catch (err) { setError(err instanceof Error ? err.message : String(err)) }
    finally { setRefreshing(false) }
  }

  if (loading) return <AdminLoading />
  if (error) return <AdminError message={error} />
  if (!data) return <AdminEmpty message="Нет данных" />

  return <div>
    <div className="admin-page-header"><div><h2 className="admin-page-title">Пропущенные must-have места</h2><p className="admin-page-subtitle">Сверка важных мест с каталогом и импортом.</p></div><button className="admin-btn admin-btn-primary" type="button" disabled={refreshing} onClick={() => void refresh()}>{refreshing ? 'Сверяем...' : 'Сверить сейчас'}</button></div>
    <div className="admin-metrics-grid admin-metrics-small"><div className="admin-metric-card"><div className="admin-metric-value">{data.summary.total}</div><div className="admin-metric-label">Всего</div></div><div className="admin-metric-card"><div className="admin-metric-value">{data.summary.matched}</div><div className="admin-metric-label">Найдено</div></div><div className="admin-metric-card"><div className="admin-metric-value">{data.summary.unresolved}</div><div className="admin-metric-label">Не закрыто</div></div><div className="admin-metric-card"><div className="admin-metric-value">{data.summary.critical_unresolved}</div><div className="admin-metric-label">Критично</div></div></div>
    {!data.items.length ? <AdminEmpty message="Список пуст" /> : <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Место</th><th>Ожидание</th><th>Статус</th><th>Причина</th><th>Матч</th><th>Действия</th></tr></thead><tbody>{data.items.map((row) => <tr key={row.id}><td><strong>{row.name}</strong><div className="admin-muted">{row.city_slug}</div></td><td><span className="admin-badge">{row.expected_category}</span><span className="admin-badge">{row.expected_scope}</span><span className="admin-badge">{row.expected_route_policy}</span></td><td><span className={`admin-badge pub-${row.status}`}>{row.status}</span></td><td>{row.gap_reason ?? '—'}</td><td>{row.matched_place_id ? <Link to={`/admin/places/${row.matched_place_id}`}>{row.matched_place_title ?? row.matched_place_id}</Link> : '—'}</td><td>{row.city_slug ? <Link className="admin-btn admin-btn-sm" to={`/admin/places?city=${row.city_slug}&q=${encodeURIComponent(row.name)}`}>Искать</Link> : null}</td></tr>)}</tbody></table></div>}
  </div>
}
