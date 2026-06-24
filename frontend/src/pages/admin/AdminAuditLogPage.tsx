import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { adminGet } from './adminApi'
import { entityText, humanizeCode } from './adminHumanText'
import type { AdminAuditLogEntry, AdminAuditLogResponse } from './adminTypes'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

const fmtDate = (iso: string) => new Date(iso).toLocaleString('ru-RU')

const ENTITY_OPTIONS = ['', 'place', 'city', 'route', 'feature_toggle', 'place_image']

export const AdminAuditLogPage = () => {
  const [params, setParams] = useSearchParams()
  const [items, setItems] = useState<AdminAuditLogEntry[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const entityType = params.get('entity_type') ?? ''
  const action = params.get('action') ?? ''
  const actor = params.get('actor') ?? ''

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    const sp = new URLSearchParams(params)
    sp.set('limit', '100')
    if (entityType) sp.set('entity_type', entityType)
    if (action) sp.set('action', action)
    if (actor) sp.set('actor', actor)
    adminGet<AdminAuditLogResponse>(`/admin/audit-log?${sp}`)
      .then((r) => { setItems(r.items); setTotal(r.total) })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [entityType, action, actor, params])

  useEffect(() => { void Promise.resolve().then(load) }, [load])

  return (
    <div>
      <h2 className="admin-page-title">Журнал действий ({total})</h2>
      <p className="admin-page-subtitle">Кто и что менял в админке.</p>
      <div className="admin-filters admin-filters-stack">
        <select value={entityType} onChange={(e) => update('entity_type', e.target.value)}>
          <option value="">Все сущности</option>
          {ENTITY_OPTIONS.filter(Boolean).map((e) => <option key={e} value={e}>{entityText(e)}</option>)}
        </select>
        <input placeholder="Действие" value={action} onChange={(e) => update('action', e.target.value)} />
        <input placeholder="Пользователь" value={actor} onChange={(e) => update('actor', e.target.value)} />
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
                  <td>{humanizeCode(e.action)}</td>
                  <td>{entityText(e.entity_type)}</td>
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

  function update(key: string, value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value); else next.delete(key)
    next.set('offset', '0')
    setParams(next)
  }
}
