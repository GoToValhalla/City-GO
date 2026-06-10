import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import type { AdminCitiesResponse } from './adminTypes'
import type { DataQualityReport } from './adminRouteTypes'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

const topCategories = (counts: Record<string, number>, n = 8) =>
  Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, n)

const placesLink = (citySlug: string, preset: string) => `/admin/places?city=${citySlug}&preset=${preset}`

export const AdminRouteDataQualityPage = () => {
  const [urlParams] = useSearchParams()
  const [cities, setCities] = useState<AdminCitiesResponse['items']>([])
  const [citySlug, setCitySlug] = useState(urlParams.get('city') ?? '')
  const [report, setReport] = useState<DataQualityReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    adminGet<AdminCitiesResponse>('/admin/cities?limit=100').then((r) => setCities(r.items)).catch(() => {})
  }, [])

  useEffect(() => {
    if (citySlug) load()
  }, [citySlug])

  const load = () => {
    if (!citySlug) return
    setLoading(true)
    setError(null)
    adminGet<DataQualityReport>(`/admin/routes/data-quality/${citySlug}`)
      .then(setReport).catch((e: Error) => setError(e.message)).finally(() => setLoading(false))
  }

  const refreshAddresses = async () => {
    if (!citySlug) return
    try {
      setActionLoading(true)
      setActionMessage('Ставлю задачу обновления адресов...')
      const result = await adminPost<{ operation_id: number; status: string }>('/admin/places/address-refresh', { city_slug: citySlug })
      setActionMessage(`Адреса поставлены в очередь: operation #${result.operation_id}, status ${result.status}`)
      load()
    } catch (e) {
      setActionMessage(e instanceof Error ? e.message : 'Не удалось запустить обновление адресов')
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) return <AdminLoading />
  if (error) return <AdminError message={error} />

  return (
    <div>
      <h2 className="admin-page-title">Маршруты → Data Quality</h2>
      <div className="admin-filters">
        <select value={citySlug} onChange={(e) => setCitySlug(e.target.value)}>
          <option value="">Город</option>
          {cities.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
        </select>
        <button type="button" className="admin-btn" onClick={load}>Показать</button>
      </div>
      {!report ? <AdminEmpty message="Выберите город" /> : (
        <div className="admin-cards">
          <section className="admin-card">
            <strong>Действия по качеству данных</strong>
            <div className="admin-filters admin-filters-stack">
              <button type="button" className="admin-btn admin-btn-primary" disabled={actionLoading} onClick={() => void refreshAddresses()}>
                Обновить адреса по городу
              </button>
              <Link className="admin-btn admin-btn-sm" to={placesLink(report.city_slug, 'no_photo')}>Открыть места без фото</Link>
              <Link className="admin-btn admin-btn-sm" to={placesLink(report.city_slug, 'no_address')}>Открыть места без адреса</Link>
              <Link className="admin-btn admin-btn-sm" to={placesLink(report.city_slug, 'no_description')}>Открыть места без описания</Link>
              <Link className="admin-btn admin-btn-sm" to={`/admin/routes/eligibility?city_slug=${report.city_slug}&issue=forbidden_category`}>Forbidden в Eligibility</Link>
            </div>
            {actionMessage ? <p className="admin-muted">{actionMessage}</p> : null}
          </section>
          <div className="admin-card"><strong>Всего</strong><div>{report.places_total}</div></div>
          <div className="admin-card"><strong>Eligible</strong><div>{report.places_eligible}</div></div>
          <div className="admin-card"><strong>Not eligible</strong><div>{report.places_not_eligible}</div></div>
          <div className="admin-card"><strong>Без фото</strong><div>{report.places_without_photo}</div></div>
          <div className="admin-card"><strong>Без адреса</strong><div>{report.places_without_address}</div></div>
          <div className="admin-card"><strong>Без описания</strong><div>{report.places_without_description}</div></div>
          <h3>ТОП категорий</h3>
          <ul>{topCategories(report.category_counts).map(([k, v]) => <li key={k}>{k}: {v}</li>)}</ul>
          <h3>ТОП запрещённых</h3>
          <ul>{topCategories(report.forbidden_category_counts).map(([k, v]) => <li key={k}>{k}: {v}</li>)}</ul>
          <h3>Quality buckets</h3>
          <ul>{Object.entries(report.quality_buckets).map(([k, v]) => <li key={k}>{k}: {v}</li>)}</ul>
          <h3>Проблемы</h3>
          <table className="admin-table"><thead><tr><th>Код</th><th>Кол-во</th><th /></tr></thead><tbody>
            {report.issues.map((i) => (
              <tr key={i.code}><td>{i.code}</td><td>{i.count}</td>
                <td><Link className="admin-btn admin-btn-sm" to={i.places_link}>Список</Link></td></tr>
            ))}
          </tbody></table>
        </div>
      )}
    </div>
  )
}
