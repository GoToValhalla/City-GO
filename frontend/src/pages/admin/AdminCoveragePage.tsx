import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet } from './adminApi'
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

export const AdminCoveragePage = () => {
  const [params] = useSearchParams()
  const [items, setItems] = useState<CoverageRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const highlight = params.get('city')

  useEffect(() => {
    adminGet<CoverageResponse>('/admin/coverage/summary?limit=100')
      .then((r) => setItems(r.items))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <AdminLoading />
  if (error) return <AdminError message={error} />
  if (!items.length) return <AdminEmpty message="Нет данных по покрытию" />

  return (
    <div>
      <h2 className="admin-page-title">Покрытие данных</h2>
      <p className="admin-page-subtitle">Качество каталога по городам</p>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Город</th><th>Оценка</th><th>Всего</th><th>Опубл.</th>
              <th>Без фото</th><th>Без адреса</th><th>Без описания</th><th>Действия</th>
            </tr>
          </thead>
          <tbody>
            {items.map((c) => (
              <tr key={c.city_id} className={highlight === c.city_slug ? 'admin-row-highlight' : ''}>
                <td><strong>{c.city_name}</strong><div className="admin-muted">{c.city_slug}</div></td>
                <td><span className={sevClass(c.severity)}>{c.quality_score}%</span></td>
                <td>{c.places_total}</td>
                <td>{c.places_published}</td>
                <td>{c.places_without_photo}</td>
                <td>{c.places_without_address}</td>
                <td>{c.places_without_description}</td>
                <td className="admin-actions-cell">
                  <Link className="admin-btn admin-btn-sm" to={`/admin/places?city=${c.city_slug}&preset=problematic`}>Проблемные</Link>
                  <Link className="admin-btn admin-btn-sm" to={`/admin/photos`}>Фото</Link>
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
