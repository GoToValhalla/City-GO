import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet } from './adminApi'
import { entityText, humanizeCode } from './adminHumanText'
import type { AdminAuditLogEntry, AdminAuditLogResponse } from './adminTypes'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

const fmtDate = (iso: string) => new Date(iso).toLocaleString('ru-RU')
const ENTITY_OPTIONS = ['', 'place', 'city', 'route', 'feature_toggle', 'place_image', 'category', 'enrichment_batch', 'import_job']
const entityUrl = (entry: AdminAuditLogEntry) => {
  if (!entry.entity_id) return null
  if (entry.entity_type === 'place') return `/admin/places/${entry.entity_id}`
  if (entry.entity_type === 'city') return `/admin/cities/${entry.entity_id}`
  if (entry.entity_type === 'category') return `/admin/taxonomy?tab=categories&category_id=${entry.entity_id}`
  if (entry.entity_type === 'place_image') return `/admin/photos?image_id=${entry.entity_id}`
  if (entry.entity_type === 'enrichment_batch') return `/admin/enrichment?batch=${entry.entity_id}`
  if (entry.entity_type === 'import_job') return `/admin/imports?job=${entry.entity_id}`
  if (entry.entity_type === 'route') return `/admin/routes/data-quality?route_id=${entry.entity_id}`
  return null
}

export const AdminAuditLogPage = () => {
  const [params, setParams] = useSearchParams(); const [items, setItems] = useState<AdminAuditLogEntry[]>([]); const [total, setTotal] = useState(0); const [loading, setLoading] = useState(true); const [error, setError] = useState<string | null>(null)
  const entityType = params.get('entity_type') ?? ''; const action = params.get('action') ?? ''; const actor = params.get('actor') ?? ''
  const load = useCallback(() => { setLoading(true); setError(null); const sp = new URLSearchParams(params); sp.set('limit', '100'); adminGet<AdminAuditLogResponse>(`/admin/audit-log?${sp}`).then((r) => { setItems(r.items); setTotal(r.total) }).catch((e: Error) => setError(e.message)).finally(() => setLoading(false)) }, [params])
  useEffect(() => { void Promise.resolve().then(load) }, [load])
  const update = (key: string, value: string) => { const next = new URLSearchParams(params); if (value) next.set(key, value); else next.delete(key); next.set('offset', '0'); setParams(next) }
  return <div>
    <h2 className="admin-page-title">Журнал действий ({total})</h2><p className="admin-page-subtitle">Сущность открывается из каждой записи; old/new данные доступны внутри строки.</p>
    <div className="admin-filters admin-filters-stack"><select value={entityType} onChange={(e) => update('entity_type', e.target.value)}><option value="">Все сущности</option>{ENTITY_OPTIONS.filter(Boolean).map((e) => <option key={e} value={e}>{entityText(e)}</option>)}</select><input placeholder="Действие" value={action} onChange={(e) => update('action', e.target.value)} /><input placeholder="Пользователь" value={actor} onChange={(e) => update('actor', e.target.value)} /><button type="button" className="admin-btn admin-btn-primary" onClick={load}>Применить</button></div>
    {error && <AdminError message={error} />}{loading ? <AdminLoading /> : items.length === 0 ? <AdminEmpty message="Событий не найдено" /> : <div className="admin-table-wrap"><table className="admin-table admin-table-compact"><thead><tr><th>Дата</th><th>Пользователь</th><th>Действие</th><th>Сущность</th><th>Причина и изменения</th></tr></thead><tbody>{items.map((entry) => { const url = entityUrl(entry); return <tr key={entry.id}><td className="admin-td-nowrap">{fmtDate(entry.created_at)}</td><td>{entry.actor}</td><td><Link to={`/admin/audit?action=${encodeURIComponent(entry.action)}`}>{humanizeCode(entry.action)}</Link></td><td>{url ? <Link to={url}>{entityText(entry.entity_type)} #{entry.entity_id}</Link> : <>{entityText(entry.entity_type)} {entry.entity_id ?? '—'}</>}</td><td>{entry.reason ?? '—'}{entry.new_value != null && <details><summary>Показать сохранённые данные</summary><pre>{JSON.stringify(entry.new_value, null, 2)}</pre></details>}</td></tr> })}</tbody></table></div>}
  </div>
}
