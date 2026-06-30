import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet } from './adminApi'
import { AdminCoverageGapsSnapshotPage } from './AdminCoverageGapsSnapshotPage'
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
  quality_score: number
  severity: string
}

type CoverageResponse = { items: CoverageRow[]; total: number }

export const AdminCoveragePage = () => {
  const [params] = useSearchParams()
  const [items, setItems] = useState<CoverageRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (params.get('tab') === 'gaps') return
    setLoading(true)
    adminGet<CoverageResponse>('/admin/coverage/summary?limit=100')
      .then((response) => setItems(response.items))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [params])

  if (params.get('tab') === 'gaps') return <AdminCoverageGapsSnapshotPage />
  if (loading) return <AdminLoading />
  if (error) return <AdminError message={error} />
  if (!items.length) return <AdminEmpty message="Нет данных по покрытию" />

  return <div>
    <div className="admin-page-header">
      <div>
        <h2 className="admin-page-title">Покрытие данных</h2>
        <p className="admin-page-subtitle">Быстрая сводка по сохранённым данным. Must-have открывает snapshot-first экран без автоматического refresh.</p>
      </div>
      <Link className="admin-btn admin-btn-primary" to="/admin/coverage?tab=gaps">Пропущенные must-have</Link>
    </div>
    <div className="admin-table-wrap">
      <table className="admin-table">
        <thead><tr><th>Город</th><th>Оценка</th><th>Всего</th><th>Опубликовано</th><th>Проблемы</th><th>Действия</th></tr></thead>
        <tbody>{items.map((city) => <tr key={city.city_id}>
          <td><Link to={`/admin/cities/${city.city_slug}?tab=quality`}><strong>{city.city_name}</strong></Link><div className="admin-muted">{city.city_slug}</div></td>
          <td><Link to={`/admin/quality?city_slug=${city.city_slug}`}>{city.quality_score}% · {city.severity}</Link></td>
          <td>{city.places_total}</td>
          <td>{city.places_published}</td>
          <td>Фото: {city.places_without_photo} · адреса: {city.places_without_address} · описания: {city.places_without_description}</td>
          <td className="admin-actions-cell"><Link className="admin-btn admin-btn-sm" to={`/admin/coverage?tab=gaps&city_slug=${city.city_slug}`}>Must-have</Link><Link className="admin-btn admin-btn-sm" to={`/admin/places?city=${city.city_slug}`}>Места</Link><Link className="admin-btn admin-btn-sm" to={`/admin/photos?city=${city.city_slug}`}>Фото</Link></td>
        </tr>)}</tbody>
      </table>
    </div>
  </div>
}
