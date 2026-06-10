import { useEffect, useState } from 'react'
import { adminGet } from './adminApi'
import type { AdminDashboard } from './adminTypes'

const METRICS: Array<[keyof AdminDashboard, string]> = [
  ['cities_total', 'Города всего'],
  ['cities_published', 'Городов активных'],
  ['places_total', 'Мест всего'],
  ['places_published', 'Мест опубликовано'],
  ['places_hidden', 'Мест скрыто'],
  ['places_needs_recheck', 'Требует проверки'],
  ['places_low_confidence', 'Низкая уверенность'],
  ['places_without_photo', 'Без фото'],
  ['pending_photos', 'Фото в очереди'],
  ['routes_total', 'Маршрутов'],
  ['routes_active', 'Маршрутов активных'],
  ['audit_events_total', 'Событий аудита'],
]

export const AdminDashboardPage = () => {
  const [data, setData] = useState<AdminDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    adminGet<AdminDashboard>('/admin/dashboard')
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="admin-state">Загрузка...</div>
  if (error) return <div className="admin-state admin-state-error">Ошибка: {error}</div>
  if (!data) return <div className="admin-state">Нет данных</div>

  return (
    <div>
      <h2 className="admin-page-title">Dashboard</h2>
      <div className="admin-metrics-grid">
        {METRICS.map(([key, label]) => (
          <div key={key} className="admin-metric-card">
            <div className="admin-metric-value">{data[key]}</div>
            <div className="admin-metric-label">{label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
