import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import { AdminRouteEligibilityDiagnostics } from './AdminRouteEligibilityDiagnostics'
import { AdminRouteEligibilityTable } from './AdminRouteEligibilityTable'
import type { AdminCitiesResponse } from './adminTypes'
import type { EligibilityResponse, RouteReadinessDiagnostics } from './adminRouteTypes'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

export const AdminRouteEligibilityPage = () => {
  const [urlParams] = useSearchParams()
  const [data, setData] = useState<EligibilityResponse | null>(null)
  const [diagnostics, setDiagnostics] = useState<RouteReadinessDiagnostics | null>(null)
  const [cities, setCities] = useState<AdminCitiesResponse['items']>([])
  const [citySlug, setCitySlug] = useState(urlParams.get('city_slug') ?? urlParams.get('city') ?? '')
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
    Promise.all([
      adminGet<EligibilityResponse>(`/admin/routes/eligibility?${sp}`),
      citySlug ? adminGet<RouteReadinessDiagnostics>(`/admin/routes/eligibility/${citySlug}`) : Promise.resolve(null),
    ])
      .then(([rows, report]) => {
        setData(rows)
        setDiagnostics(report)
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [citySlug, eligible, issue])

  useEffect(() => {
    adminGet<AdminCitiesResponse>('/admin/cities?limit=100').then((r) => setCities(r.items)).catch(() => {})
    void Promise.resolve().then(load)
  }, [load])

  const bulk = async (action: string) => {
    const ids = [...selected]
    if (!ids.length || !window.confirm(`Применить ${action} к ${ids.length} местам?`)) return
    const params = action === 'disable_route' ? { reason: 'eligibility_dashboard' } : {}
    await adminPost('/admin/places/bulk/apply', { place_ids: ids, action, params, confirm: true })
    setSelected(new Set())
    load()
  }

  const toggleSelected = (placeId: number) => {
    setSelected((current) => {
      const next = new Set(current)
      if (next.has(placeId)) {
        next.delete(placeId)
      } else {
        next.add(placeId)
      }
      return next
    })
  }

  if (loading && !data) return <AdminLoading />
  if (error) return <AdminError message={error} />

  return (
    <div>
      <h2 className="admin-page-title">Маршруты → Eligibility</h2>
      <div className="admin-filters">
        <select value={citySlug} onChange={(e) => setCitySlug(e.target.value)}>
          <option value="">Все города</option>
          {cities.map((city) => <option key={city.slug} value={city.slug}>{city.name}</option>)}
        </select>
        <input placeholder="city_slug" value={citySlug} onChange={(e) => setCitySlug(e.target.value)} />
        <select value={eligible} onChange={(e) => setEligible(e.target.value)}>
          <option value="">Eligible: все</option>
          <option value="true">Eligible</option>
          <option value="false">Not eligible</option>
        </select>
        <input placeholder="issue code" value={issue} onChange={(e) => setIssue(e.target.value)} />
        <button type="button" className="admin-btn admin-btn-sm" onClick={load}>Обновить</button>
        <button type="button" className="admin-btn admin-btn-sm" onClick={() => void bulk('disable_route')}>Исключить</button>
        <button type="button" className="admin-btn admin-btn-sm" onClick={() => void bulk('enable_route')}>Включить</button>
      </div>
      {diagnostics
        ? <AdminRouteEligibilityDiagnostics report={diagnostics} />
        : <AdminEmpty message="Выберите город, чтобы увидеть Route Readiness Diagnostics" />}
      <AdminRouteEligibilityTable items={data?.items ?? []} selected={selected} onToggle={toggleSelected} />
    </div>
  )
}
