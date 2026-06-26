import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet } from './adminApi'
import { AdminCoverageGapsPage } from './AdminCoverageGapsPage'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

type CoverageRow = {
  city_id: number
  city_slug: string
  city_name: string
  places_total: number
  places_published: number
  places_without_photo: number
  places_without_address: number
  places_without_description: number
  places_route_eligible: number
  places_not_route_eligible: number
  pending_photos: number
  quality_score: number
  severity: string
}

type CoverageResponse = { items: CoverageRow[]; total: number }

const sevClass = (s: string) => `admin-quality admin-quality-${s}`
const placesLink = (city: string, extra = '') => `/admin/places?city=${encodeURIComponent(city)}${extra}`
const CountLink = ({ to, value, label }: { to: string; value: number; label: string }) => <Link to={to} title={`Открыть: ${label}`}>{value}</Link>

export const AdminCoveragePage = () => {
  const [params] = useSearchParams()
  const [items, setItems] = useState<CoverageRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const highlight = params.get('city')

  useEffect(() => {
    if (params.get('tab') === 'gaps') return
    adminGet<CoverageResponse>('/admin/coverage/summary?limit=100')
      .then((r) => setItems(r.items))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [params])

  if (params.get('tab') === 'gaps') {
    return <AdminCoverageGapsPage />
  }

  if (loading) return <AdminLoading />
  if (error) return <AdminError message={error} />
  if (!items.length) return <AdminEmpty message="Нет данных по покрытию" />

  return (
    <div>
      <div className="admin-page-header">
        <div>
          <h2 className="admin-page-title">Покрытие данных</h2>
          <p className="admin-page-subtitle">Каждое число открывает соответствующий набор мест с сохранённым городом и фильтром.</p>
        </div>
        <Link className="admin-btn admin-btn-primary" to="/admin/coverage?tab=gaps">Пропущенные must-have</Link>
      </div>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead><tr><th>Город</th><th>Оценка</th><th>Всего</th><th>Опубл.</th><th>Без фото</th><th>Без адреса</th><th>Без описания</th><th>Действия</th></tr></thead>
          <tbody>
            {items.map((c) => (
              <tr key={c.city_id} className={highlight === c.city_slug ? 'admin-row-highlight' : ''}>
                <td><Link to={`/admin/cities/${c.city_slug}?tab=quality`}><strong>{c.city_name}</strong></Link><div className="admin-muted">{c.city_slug}</div></td>
                <td><Link to={`/admin/quality?city_slug=${c.city_slug}`} className={sevClass(c.severity)}>{c.quality_score}%</Link></td>
                <td><CountLink to={placesLink(c.city_slug)} value={c.places_total} label="все места" /></td>
                <td><CountLink to={placesLink(c.city_slug, '&publication=published')} value={c.places_published} label="опубликованные места" /></td>
                <td><CountLink to={placesLink(c.city_slug, '&photo=false')} value={c.places_without_photo} label="места без фото" /></td>
                <td><CountLink to={placesLink(c.city_slug, '&address=false')} value={c.places_without_address} label="места без адреса" /></td>
                <td><CountLink to={placesLink(c.city_slug, '&description=false')} value={c.places_without_description} label="места без описания" /></td>
                <td className="admin-actions-cell">
                  <Link className="admin-btn admin-btn-sm" to={placesLink(c.city_slug, '&preset=problematic')}>Проблемные</Link>
                  <Link className="admin-btn admin-btn-sm" to={`/admin/coverage?tab=gaps&city_slug=${c.city_slug}`}>Must-have</Link>
                  <Link className="admin-btn admin-btn-sm" to={`/admin/photos?city=${c.city_slug}`}>Фото</Link>
                  <Link className="admin-btn admin-btn-sm" to={`/admin/enrichment?city=${c.city_slug}`}>Обогащение</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
