import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import type { AdminCitiesResponse } from './adminTypes'
import type { EligibilityResponse } from './adminRouteTypes'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

export const AdminRouteEligibilityPage = () => {
  const [urlParams] = useSearchParams()
  const [data, setData] = useState<EligibilityResponse | null>(null)
  const [cities, setCities] = useState<AdminCitiesResponse['items']>([])
  const [citySlug, setCitySlug] = useState(urlParams.get('city') ?? '')
  const [eligible, setEligible] = useState('')
  const [issue, setIssue] = useState(urlParams.get('issue') ?? '')
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    const sp = new URLSearchParams({ limit: '50', offset: '0' })
    if (citySlug) sp.set('city_slug', citySlug)
    if (eligible) sp.set('eligible', eligible)
    if (issue) sp.set('issue', issue)
    adminGet<EligibilityResponse>(`/admin/routes/eligibility?${sp}`)
      .then(setData).catch((e: Error) => setError(e.message)).finally(() => setLoading(false))
  }, [citySlug, eligible, issue])

  useEffect(() => {
    adminGet<AdminCitiesResponse>('/admin/cities?limit=100').then((r) => setCities(r.items)).catch(() => {})
    load()
  }, [load])

  const bulk = async (action: string) => {
    const ids = [...selected]
    if (!ids.length || !window.confirm(`Применить ${action} к ${ids.length} местам?`)) return
    const params = action === 'disable_route' ? { reason: 'eligibility_dashboard' } : {}
    await adminPost('/admin/places/bulk/apply', { place_ids: ids, action, params, confirm: true })
    setSelected(new Set())
    load()
  }

  if (loading && !data) return <AdminLoading />
  if (error) return <AdminError message={error} />

  return (
    <div>
      <h2 className="admin-page-title">Маршруты → Eligibility</h2>
      <div className="admin-filters">
        <select value={citySlug} onChange={(e) => setCitySlug(e.target.value)}>
          <option value="">Все города</option>
          {cities.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
        </select>
        <select value={eligible} onChange={(e) => setEligible(e.target.value)}>
          <option value="">Eligible: все</option>
          <option value="true">Eligible</option>
          <option value="false">Not eligible</option>
        </select>
        <input placeholder="issue code" value={issue} onChange={(e) => setIssue(e.target.value)} />
        <button type="button" className="admin-btn admin-btn-sm" onClick={load}>Обновить</button>
        <button type="button" className="admin-btn admin-btn-sm" onClick={() => bulk('disable_route')}>Исключить</button>
        <button type="button" className="admin-btn admin-btn-sm" onClick={() => bulk('enable_route')}>Включить</button>
      </div>
      {!data?.items.length ? <AdminEmpty message="Нет мест" /> : (
        <table className="admin-table">
          <thead><tr><th /><th>Место</th><th>Категория</th><th>Eligible</th><th>Quality</th><th>Reason</th></tr></thead>
          <tbody>
            {data.items.map((row) => (
              <tr key={row.place_id}>
                <td><input type="checkbox" checked={selected.has(row.place_id)} onChange={() => setSelected((s) => { const n = new Set(s); n.has(row.place_id) ? n.delete(row.place_id) : n.add(row.place_id); return n })} /></td>
                <td><Link to={`/admin/places/${row.place_id}`}>{row.title}</Link></td>
                <td>{row.category ?? '—'}</td>
                <td>{row.eligible ? '✓' : '✗'}</td>
                <td>{row.quality_score} ({row.quality_bucket})</td>
                <td>{row.primary_reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
