import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet, adminPatch, adminPost } from './adminApi'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

type Row = {
  id: number
  city_slug: string | null
  name: string
  expected_category: string
  expected_scope: string
  expected_route_policy: string
  status: string
  gap_reason?: string | null
  review_notes?: string | null
  matched_place_id?: number | null
  matched_place_title?: string | null
}

type Payload = {
  items: Row[]
  total: number
  summary: {
    total: number
    matched: number
    unresolved: number
    critical_unresolved: number
    by_status?: Record<string, number>
    by_gap_reason?: Record<string, number>
    by_expected_category?: Record<string, number>
  }
  filters?: Record<string, string | null>
}

const statusOptions = ['', 'unresolved', 'critical', 'missing', 'matched', 'needs_review', 'source_absent', 'out_of_scope', 'tag_unsupported', 'rejected_policy', 'duplicate']
const reasonOptions = ['', 'outside_bbox', 'unsupported_tag', 'source_absent', 'hidden_by_policy', 'missing_name', 'missing_coordinates', 'duplicate_candidate', 'not_imported_scope', 'not_visible_in_catalog', 'not_route_eligible']
const categoryOptions = ['', 'culture', 'food', 'walk', 'park', 'museum', 'viewpoint', 'cafe']

const metricLink = (label: string, value: number, params: URLSearchParams, patch: Record<string, string>) => {
  const next = new URLSearchParams(params)
  next.set('tab', 'gaps')
  Object.entries(patch).forEach(([key, val]) => val ? next.set(key, val) : next.delete(key))
  return <Link className="admin-metric-card admin-metric-link" to={`/admin/coverage?${next.toString()}`}>
    <div className="admin-metric-value">{value}</div><div className="admin-metric-label">{label}</div>
  </Link>
}

const valueOrEmpty = (params: URLSearchParams, key: string) => params.get(key) ?? ''

export const AdminCoverageGapsPage = () => {
  const [params, setParams] = useSearchParams()
  const [data, setData] = useState<Payload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [updatingId, setUpdatingId] = useState<number | null>(null)

  const query = useMemo(() => {
    const api = new URLSearchParams()
    for (const key of ['city_slug', 'status', 'gap_reason', 'expected_category']) {
      const value = params.get(key)
      if (value) api.set(key, value)
    }
    api.set('limit', '300')
    return api.toString()
  }, [params])

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    adminGet<Payload>(`/admin/coverage-gaps?${query}`)
      .then(setData)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [query])

  useEffect(() => { load() }, [load])

  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    next.set('tab', 'gaps')
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next)
  }

  const refresh = async () => {
    setRefreshing(true)
    setError(null)
    try {
      const city = params.get('city_slug')
      await adminPost(`/admin/coverage-gaps/refresh${city ? `?city_slug=${encodeURIComponent(city)}` : ''}`)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setRefreshing(false)
    }
  }

  const mark = async (row: Row, status: string, gap_reason?: string | null) => {
    setUpdatingId(row.id)
    setError(null)
    try {
      await adminPatch(`/admin/coverage-gaps/${row.id}`, {
        status,
        gap_reason: gap_reason ?? null,
        review_notes: `Admin action from Coverage Gaps UI: ${status}${gap_reason ? ` / ${gap_reason}` : ''}`,
      })
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setUpdatingId(null)
    }
  }

  if (loading) return <AdminLoading />
  if (error) return <AdminError message={error} />
  if (!data) return <AdminEmpty message="Нет данных" />

  return <div>
    <div className="admin-page-header">
      <div>
        <h2 className="admin-page-title">Пропущенные must-have места</h2>
        <p className="admin-page-subtitle">Сверка важных мест с каталогом, импортом и source observations. Метрики открывают точный отфильтрованный набор.</p>
      </div>
      <button className="admin-btn admin-btn-primary" type="button" disabled={refreshing} onClick={() => void refresh()}>{refreshing ? 'Сверяем...' : 'Сверить сейчас'}</button>
    </div>

    <div className="admin-metrics-grid admin-metrics-small">
      {metricLink('Всего', data.summary.total, params, { status: '', gap_reason: '', expected_category: '' })}
      {metricLink('Найдено', data.summary.matched, params, { status: 'matched' })}
      {metricLink('Не закрыто', data.summary.unresolved, params, { status: 'unresolved', gap_reason: '' })}
      {metricLink('Критично', data.summary.critical_unresolved, params, { status: 'critical', gap_reason: '' })}
    </div>

    <div className="admin-card admin-filter-panel">
      <label>Город<input className="admin-input" value={valueOrEmpty(params, 'city_slug')} onChange={(e) => setFilter('city_slug', e.target.value)} placeholder="kutaisi" /></label>
      <label>Статус<select className="admin-input" value={valueOrEmpty(params, 'status')} onChange={(e) => setFilter('status', e.target.value)}>{statusOptions.map((v) => <option key={v} value={v}>{v || 'Все'}</option>)}</select></label>
      <label>Причина<select className="admin-input" value={valueOrEmpty(params, 'gap_reason')} onChange={(e) => setFilter('gap_reason', e.target.value)}>{reasonOptions.map((v) => <option key={v} value={v}>{v || 'Все'}</option>)}</select></label>
      <label>Категория<select className="admin-input" value={valueOrEmpty(params, 'expected_category')} onChange={(e) => setFilter('expected_category', e.target.value)}>{categoryOptions.map((v) => <option key={v} value={v}>{v || 'Все'}</option>)}</select></label>
    </div>

    {!data.items.length ? <AdminEmpty message="Список пуст" /> : <div className="admin-table-wrap"><table className="admin-table">
      <thead><tr><th>Место</th><th>Ожидание</th><th>Статус</th><th>Причина</th><th>Матч</th><th>Действия</th></tr></thead>
      <tbody>{data.items.map((row) => <tr key={row.id}>
        <td><strong>{row.name}</strong><div className="admin-muted">{row.city_slug} · #{row.id}</div>{row.review_notes ? <div className="admin-muted">{row.review_notes}</div> : null}</td>
        <td><span className="admin-badge">{row.expected_category}</span><span className="admin-badge">{row.expected_scope}</span><span className="admin-badge">{row.expected_route_policy}</span></td>
        <td><Link to={`/admin/coverage?tab=gaps&status=${row.status}`} className={`admin-badge pub-${row.status}`}>{row.status}</Link></td>
        <td>{row.gap_reason ? <Link to={`/admin/coverage?tab=gaps&gap_reason=${row.gap_reason}`}>{row.gap_reason}</Link> : '—'}</td>
        <td>{row.matched_place_id ? <Link to={`/admin/places/${row.matched_place_id}`}>{row.matched_place_title ?? row.matched_place_id}</Link> : '—'}</td>
        <td className="admin-actions-cell">
          {row.city_slug ? <Link className="admin-btn admin-btn-sm" to={`/admin/places?city=${row.city_slug}&q=${encodeURIComponent(row.name)}`}>Искать</Link> : null}
          <button className="admin-btn admin-btn-sm" disabled={updatingId === row.id} type="button" onClick={() => void mark(row, 'needs_review', row.gap_reason ?? 'not_visible_in_catalog')}>На проверку</button>
          <button className="admin-btn admin-btn-sm" disabled={updatingId === row.id} type="button" onClick={() => void mark(row, 'source_absent', 'source_absent')}>Нет в источнике</button>
          <button className="admin-btn admin-btn-sm" disabled={updatingId === row.id} type="button" onClick={() => void mark(row, 'duplicate', 'duplicate_candidate')}>Дубль</button>
        </td>
      </tr>)}</tbody>
    </table></div>}
  </div>
}
