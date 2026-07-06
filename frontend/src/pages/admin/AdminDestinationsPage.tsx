import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminGet } from './adminApi'
import { AdminLoading, AdminSectionError } from './shared/AdminStates'
import './AdminDataPipeline.css'

type DestinationRow = {
  id: number
  slug: string
  title: string
  destination_type: string
  places_count: number
}

const TYPE_LABELS: Record<string, string> = {
  city: 'Город',
  region: 'Регион',
  natural_region: 'Природный регион',
  national_park: 'Национальный парк',
  tourist_cluster: 'Туристический кластер',
  route_corridor: 'Коридор маршрута',
  remote_area: 'Удалённая территория',
}

export const AdminDestinationsPage = () => {
  const [items, setItems] = useState<DestinationRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await adminGet<{ items: DestinationRow[] }>('/admin/destinations')
      setItems(data.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить направления')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  if (loading) return <AdminLoading message="Загрузка направлений…" />
  if (error) return <AdminSectionError title="Ошибка" message={error} onRetry={() => void load()} />

  return (
    <div className="admin-data-pipeline" data-testid="admin-destinations">
      <header className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Направления</h1>
          <p className="admin-page-subtitle">Destination-first каталог и контуры импорта/маршрутов.</p>
        </div>
      </header>
      <section className="admin-section admin-readonly-zone">
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Название</th><th>Тип</th><th>Мест</th><th /></tr></thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id}>
                  <td>{row.title}</td>
                  <td>{TYPE_LABELS[row.destination_type] ?? row.destination_type}</td>
                  <td>{row.places_count}</td>
                  <td><Link to={`/admin/destinations/${row.slug}`}>Открыть</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
