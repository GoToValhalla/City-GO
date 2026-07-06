import { type FormEvent, useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import { AdminLoading, AdminSectionError } from './shared/AdminStates'
import './AdminDataPipeline.css'

type DestinationDetail = {
  slug: string
  title: string
  destination_type: string
  places_count: number
  scopes: { id: number; code: string; name: string; scope_type: string; enabled: boolean }[]
}

type MembershipRow = {
  id: number
  place_id: number
  assignment_type: string
  is_primary: boolean
  is_hidden: boolean
}

type OrphanRow = { id: number; slug: string; title: string }

const TYPE_LABELS: Record<string, string> = {
  city: 'Город',
  region: 'Регион',
  natural_region: 'Природный регион',
  national_park: 'Национальный парк',
  tourist_cluster: 'Туристический кластер',
  route_corridor: 'Коридор маршрута',
  remote_area: 'Удалённая территория',
}

export const AdminDestinationDetailPage = () => {
  const { slug = '' } = useParams()
  const [detail, setDetail] = useState<DestinationDetail | null>(null)
  const [memberships, setMemberships] = useState<MembershipRow[]>([])
  const [orphans, setOrphans] = useState<OrphanRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [scopeCode, setScopeCode] = useState('catalog-core')
  const [scopeName, setScopeName] = useState('Основной каталог')
  const [scopeBbox, setScopeBbox] = useState('{"south":54.5,"north":55.0,"west":20.0,"east":21.0}')
  const [assignPlaceId, setAssignPlaceId] = useState('')
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!slug) return
    setLoading(true)
    setError(null)
    try {
      const [dest, mem, orph] = await Promise.all([
        adminGet<DestinationDetail>(`/admin/destinations/${slug}`),
        adminGet<MembershipRow[]>(`/admin/destinations/${slug}/memberships`),
        adminGet<OrphanRow[]>('/admin/destinations/orphans/places?limit=20'),
      ])
      setDetail(dest)
      setMemberships(mem)
      setOrphans(orph)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить направление')
    } finally {
      setLoading(false)
    }
  }, [slug])

  useEffect(() => { void load() }, [load])

  const onCreateScope = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setFormError(null)
    try {
      const bbox = JSON.parse(scopeBbox) as Record<string, number>
      await adminPost(`/admin/destinations/${slug}/scopes`, {
        code: scopeCode,
        name: scopeName,
        scope_type: 'catalog',
        import_strategy: 'single_bbox',
        bbox,
        enabled: true,
      })
      await load()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Не удалось создать контур')
    } finally {
      setSaving(false)
    }
  }

  const onAssignPlace = async (e: FormEvent) => {
    e.preventDefault()
    const placeId = Number(assignPlaceId)
    if (!Number.isFinite(placeId)) {
      setFormError('Укажите числовой идентификатор места')
      return
    }
    setSaving(true)
    setFormError(null)
    try {
      await adminPost(`/admin/destinations/${slug}/assign-place`, { place_id: placeId, is_primary: false })
      setAssignPlaceId('')
      await load()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Не удалось назначить место')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <AdminLoading message="Загрузка направления…" />
  if (error || !detail) {
    return <AdminSectionError title="Ошибка" message={error ?? 'Направление не найдено'} onRetry={() => void load()} />
  }

  return (
    <div className="admin-data-pipeline" data-testid="admin-destination-detail">
      <header className="admin-page-header">
        <div>
          <p className="admin-page-subtitle"><Link to="/admin/destinations">← Направления</Link></p>
          <h1 className="admin-page-title">{detail.title}</h1>
          <p className="admin-page-subtitle">
            {TYPE_LABELS[detail.destination_type] ?? detail.destination_type} · {detail.places_count} мест
          </p>
        </div>
      </header>

      {formError ? <div className="admin-state admin-state-error">{formError}</div> : null}

      <section className="admin-section">
        <h2 className="admin-section-title">Контуры</h2>
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Код</th><th>Название</th><th>Тип</th><th>Статус</th></tr></thead>
            <tbody>
              {detail.scopes.map((s) => (
                <tr key={s.id}><td>{s.code}</td><td>{s.name}</td><td>{s.scope_type}</td><td>{s.enabled ? 'Включён' : 'Выключен'}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <form className="admin-form-grid" onSubmit={(e) => void onCreateScope(e)}>
          <input value={scopeCode} onChange={(e) => setScopeCode(e.target.value)} placeholder="Код контура" required />
          <input value={scopeName} onChange={(e) => setScopeName(e.target.value)} placeholder="Название" required />
          <textarea value={scopeBbox} onChange={(e) => setScopeBbox(e.target.value)} rows={3} aria-label="BBox JSON" />
          <button type="submit" className="admin-btn admin-btn-safe" disabled={saving}>{saving ? 'Сохранение…' : 'Добавить контур'}</button>
        </form>
      </section>

      <section className="admin-section">
        <h2 className="admin-section-title">Членства мест</h2>
        <div className="admin-table-wrap">
          <table className="admin-table" data-testid="memberships-table">
            <thead><tr><th>Место</th><th>Тип</th><th>Основное</th><th>Скрыто</th></tr></thead>
            <tbody>
              {memberships.map((m) => (
                <tr key={m.id}>
                  <td>{m.place_id}</td>
                  <td>{m.assignment_type}</td>
                  <td>{m.is_primary ? 'Да' : 'Нет'}</td>
                  <td>{m.is_hidden ? 'Да' : 'Нет'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <form className="admin-form-grid" onSubmit={(e) => void onAssignPlace(e)}>
          <input value={assignPlaceId} onChange={(e) => setAssignPlaceId(e.target.value)} placeholder="ID места" />
          <button type="submit" className="admin-btn admin-btn-safe" disabled={saving}>Назначить вручную</button>
        </form>
      </section>

      <section className="admin-section">
        <h2 className="admin-section-title">Места без направления</h2>
        <div className="admin-table-wrap">
          <table className="admin-table" data-testid="orphans-table">
            <thead><tr><th>ID</th><th>Название</th><th>Slug</th></tr></thead>
            <tbody>
              {orphans.map((o) => (
                <tr key={o.id}><td>{o.id}</td><td>{o.title}</td><td>{o.slug}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
