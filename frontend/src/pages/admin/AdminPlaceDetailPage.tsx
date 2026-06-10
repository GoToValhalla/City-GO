import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { adminGet, adminPatch, adminPost } from './adminApi'
import { AdminError, AdminLoading } from './shared/AdminStates'

type Detail = {
  id: number; title: string; city_name: string; category: string | null; address: string | null
  address_source: string | null; address_confidence: number | null; address_updated_at: string | null
  visible_to_users: boolean; route_enabled: boolean; publication_status: string
  verification_status: string; route_usage_count: number; route_usage_note: string | null
  short_description: string | null; source: string | null; admin_comment: string | null
  tags: Array<{ id: number; name: string }>; audit_history: Array<{ action: string; actor: string; created_at: string }>
}

export const AdminPlaceDetailPage = () => {
  const { id } = useParams()
  const [data, setData] = useState<Detail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    if (!id) return
    setLoading(true)
    adminGet<Detail>(`/admin/places/${id}/detail`)
      .then(setData).catch((e: Error) => setError(e.message)).finally(() => setLoading(false))
  }, [id])

  useEffect(() => { load() }, [load])

  const action = async (fields: object) => {
    if (!id) return
    setBusy(true)
    try {
      await adminPatch(`/admin/places/${id}`, fields)
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка')
    } finally { setBusy(false) }
  }

  const refreshAddress = async () => {
    if (!id || !window.confirm('Обновить адрес через геокодинг?')) return
    setBusy(true)
    try {
      await adminPost('/admin/places/address-refresh', { place_ids: [Number(id)] })
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка')
    } finally { setBusy(false) }
  }

  if (loading) return <AdminLoading />
  if (error) return <AdminError message={error} />
  if (!data) return null

  return (
    <div>
      <Link to="/admin/places" className="admin-muted">← К списку мест</Link>
      <h2 className="admin-page-title">{data.title}</h2>
      <p className="admin-page-subtitle">{data.city_name} · {data.category ?? '—'}</p>
      <div className="admin-detail-panel">
        <p><strong>Адрес:</strong> {data.address ?? '—'} {data.address_source && <span className="admin-muted">({data.address_source})</span>}</p>
        <p><strong>Статус:</strong> {data.publication_status} · <strong>Верификация:</strong> {data.verification_status}</p>
        <p><strong>Видимость:</strong> {data.visible_to_users ? 'да' : 'нет'} · <strong>В маршрутах:</strong> {data.route_enabled ? 'да' : 'нет'}</p>
        <p><strong>Использование в маршрутах:</strong> {data.route_usage_count} <span className="admin-muted">{data.route_usage_note}</span></p>
        <div className="admin-actions-cell" style={{ marginTop: 12 }}>
          <button disabled={busy} className="admin-btn admin-btn-sm" onClick={() => action({ publication_status: 'published' })}>Опубликовать</button>
          <button disabled={busy} className="admin-btn admin-btn-sm" onClick={() => action({ publication_status: 'needs_review' })}>На проверку</button>
          <button disabled={busy} className="admin-btn admin-btn-sm" onClick={() => action({ visible_to_users: !data.visible_to_users })}>Видимость</button>
          <button disabled={busy} className="admin-btn admin-btn-sm" onClick={() => action({ route_enabled: !data.route_enabled })}>Маршруты</button>
          <button disabled={busy} className="admin-btn admin-btn-sm" onClick={refreshAddress}>Обновить адрес</button>
          <Link className="admin-btn admin-btn-sm" to={`/admin/audit?entity_id=${data.id}`}>Аудит</Link>
        </div>
      </div>
      {data.audit_history.length > 0 && (
        <div className="admin-detail-panel">
          <h3>История изменений</h3>
          <ul>{data.audit_history.map((a, i) => (
            <li key={i}><code>{a.action}</code> — {a.actor} — {new Date(a.created_at).toLocaleString('ru-RU')}</li>
          ))}</ul>
        </div>
      )}
    </div>
  )
}
