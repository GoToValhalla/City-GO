import { type FormEvent, useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
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
  const navigate = useNavigate()
  const [items, setItems] = useState<DestinationRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({ name: '', slug: '', destination_type: 'tourist_cluster', center_lat: '', center_lng: '' })

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

  const updateName = (name: string) => {
    setForm((current) => ({ ...current, name, slug: current.slug || suggestSlug(name) }))
  }

  const submitCreate = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const body = {
        name: form.name,
        slug: form.slug,
        destination_type: form.destination_type,
        center_lat: form.center_lat ? Number(form.center_lat) : null,
        center_lng: form.center_lng ? Number(form.center_lng) : null,
      }
      const created = await adminPost<DestinationRow>('/admin/destinations', body)
      navigate(`/admin/destinations/${created.slug}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать направление')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <AdminLoading message="Загрузка направлений…" />
  if (error) return <AdminSectionError title="Ошибка" message={error} onRetry={() => void load()} />

  return (
    <div className="admin-data-pipeline" data-testid="admin-destinations">
      <header className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Направления</h1>
          <p className="admin-page-subtitle">Каталоги направлений, контуры сбора данных и готовность маршрутов.</p>
        </div>
        <button type="button" className="admin-btn admin-btn-primary" onClick={() => setShowCreate((value) => !value)}>
          {showCreate ? 'Скрыть форму' : 'Создать направление'}
        </button>
      </header>

      {(showCreate || items.length === 0) ? (
        <section className="admin-section" data-testid="destination-create-form">
          <h2 className="admin-section-title">{items.length ? 'Новое направление' : 'Создайте первое направление'}</h2>
          <form className="admin-form-grid" onSubmit={(event) => void submitCreate(event)}>
            <label className="admin-field"><span>Название</span><input value={form.name} onChange={(event) => updateName(event.target.value)} required /></label>
            <label className="admin-field"><span>Slug</span><input value={form.slug} onChange={(event) => setForm((current) => ({ ...current, slug: event.target.value }))} required /></label>
            <label className="admin-field"><span>Тип</span><select value={form.destination_type} onChange={(event) => setForm((current) => ({ ...current, destination_type: event.target.value }))}>{Object.entries(TYPE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <label className="admin-field"><span>Широта центра</span><input inputMode="decimal" value={form.center_lat} onChange={(event) => setForm((current) => ({ ...current, center_lat: event.target.value }))} /></label>
            <label className="admin-field"><span>Долгота центра</span><input inputMode="decimal" value={form.center_lng} onChange={(event) => setForm((current) => ({ ...current, center_lng: event.target.value }))} /></label>
            <button type="submit" className="admin-btn admin-btn-safe" disabled={saving}>{saving ? 'Создание…' : 'Создать'}</button>
          </form>
        </section>
      ) : null}

      {!items.length ? <section className="admin-section admin-empty-state"><p>Направлений пока нет. После создания добавьте контур сбора данных и запустите сбор мест.</p></section> : null}
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

const suggestSlug = (value: string) => value.toLowerCase()
  .replace(/[а]/g, 'a').replace(/[б]/g, 'b').replace(/[в]/g, 'v').replace(/[г]/g, 'g')
  .replace(/[д]/g, 'd').replace(/[её]/g, 'e').replace(/[ж]/g, 'zh').replace(/[з]/g, 'z')
  .replace(/[и]/g, 'i').replace(/[й]/g, 'y').replace(/[к]/g, 'k').replace(/[л]/g, 'l')
  .replace(/[м]/g, 'm').replace(/[н]/g, 'n').replace(/[о]/g, 'o').replace(/[п]/g, 'p')
  .replace(/[р]/g, 'r').replace(/[с]/g, 's').replace(/[т]/g, 't').replace(/[у]/g, 'u')
  .replace(/[ф]/g, 'f').replace(/[х]/g, 'h').replace(/[ц]/g, 'c').replace(/[ч]/g, 'ch')
  .replace(/[шщ]/g, 'sh').replace(/[ы]/g, 'y').replace(/[э]/g, 'e').replace(/[ю]/g, 'yu')
  .replace(/[я]/g, 'ya').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
