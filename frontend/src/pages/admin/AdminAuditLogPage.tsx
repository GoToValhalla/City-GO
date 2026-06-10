import { useCallback, useEffect, useState } from 'react'
import { adminGet } from './adminApi'
import type { AdminAuditLogEntry, AdminAuditLogResponse } from './adminTypes'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

const fmtDate = (iso: string) => new Date(iso).toLocaleString('ru-RU')

const ENTITY_OPTIONS = ['', 'place', 'city', 'route', 'feature_toggle', 'place_image']

export const AdminAuditLogPage = () => {
  const [items, setItems] = useState<AdminAuditLogEntry[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [entityType, setEntityType] = useState('')
  const [action, setAction] = useState('')
  const [actor, setActor] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    const sp = new URLSearchParams({ limit: '100', offset: '0' })
    if (entityType) sp.set('entity_type', entityType)
    if (action) sp.set('action', action)
    if (actor) sp.set('actor', actor)
    adminGet<AdminAuditLogResponse>(`/admin/audit-log?${sp}`)
      .then((r) => { setItems(r.items); setTotal(r.total) })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [entityType, action, actor])

  useEffect(() => { void Promise.resolve().then(load) }, [load])

  return (
    <div>
      <h2 className="admin-page-title">Журнал аудита ({total})</h2>
      <div className="admin-filters admin-filters-stack">
        <select value={entityType} onChange={(e) => setEntityType(e.target.value)}>
          <option value="">Все сущности</option>
          {ENTITY_OPTIONS.filter(Boolean).map((e) => <option key={e} value={e}>{e}</option>)}
        </select>
        <input placeholder="Действие (action)" value={action} onChange={(e) => setAction(e.target.value)} />
        <input placeholder="Пользователь" value={actor} onChange={(e) => setActor(e.target.value)} />
        <button type="button" className="admin-btn admin-btn-primary" onClick={load}>Применить</button>
      </div>
      {error && <AdminError message={error} />}
      {loading ? <AdminLoading /> : items.length === 0 ? <AdminEmpty message="Событий не найдено" /> : (
        <div className="admin-table-wrap">
          <table className="admin-table admin-table-compact">
            <thead>
              <tr><th>Дата</th><th>Пользователь</th><th>Действие</th><th>Сущность</th><th>ID</th><th>Причина</th></tr>
            </thead>
            <tbody>
              {items.map((e) => (
                <tr key={e.id}>
                  <td className="admin-td-nowrap">{fmtDate(e.created_at)}</td>
                  <td>{e.actor}</td>
                  <td><code>{e.action}</code></td>
                  <td>{e.entity_type}</td>
                  <td>{e.entity_id ?? '—'}</td>
                  <td>{e.reason ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
