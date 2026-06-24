import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet } from './adminApi'
import { logLevelText } from './adminHumanText'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

type Log = { id: number; level: string; module: string; message: string; details: Record<string, unknown> | null; city_slug: string | null; request_id: string | null; created_at: string }
const KEYS = ['q', 'level', 'module', 'city_slug', 'request_id', 'place_id', 'route_id', 'actor_id', 'environment'] as const
const numericDetail = (details: Record<string, unknown> | null, key: string) => {
  const value = details?.[key]
  return typeof value === 'number' || (typeof value === 'string' && /^\d+$/.test(value)) ? String(value) : null
}

export const AdminSystemLogsPage = () => {
  const [params, setParams] = useSearchParams(); const [items, setItems] = useState<Log[]>([]); const [total, setTotal] = useState(0); const [loading, setLoading] = useState(true); const [error, setError] = useState<string | null>(null); const offset = Number(params.get('offset') ?? 0)
  const load = useCallback(() => { setLoading(true); setError(null); const query = new URLSearchParams(params); query.set('limit', '50'); adminGet<{ items: Log[]; total: number }>(`/admin/system-logs?${query}`).then((row) => { setItems(row.items); setTotal(row.total) }).catch((e: Error) => setError(e.message)).finally(() => setLoading(false)) }, [params])
  useEffect(() => { void Promise.resolve().then(load) }, [load])
  const update = (key: string, value: string) => { const next = new URLSearchParams(params); if (value) next.set(key, value); else next.delete(key); if (key !== 'offset') next.set('offset', '0'); setParams(next) }
  return <div>
    <h2 className="admin-page-title">Системные логи ({total})</h2><p className="admin-page-subtitle">Request ID, город и сущности открывают связанные записи без потери текущего контекста.</p>
    <div className="admin-filter-card admin-filter-grid">{KEYS.map((key) => key === 'level' ? <label className="admin-field" key={key}><span>Уровень</span><select value={params.get(key) ?? ''} onChange={(e) => update(key, e.target.value)}><option value="">Все</option>{['info', 'warning', 'error', 'critical'].map((level) => <option key={level} value={level}>{logLevelText(level)}</option>)}</select></label> : <label className="admin-field" key={key}><span>{LABELS[key]}</span><input value={params.get(key) ?? ''} onChange={(e) => update(key, e.target.value)} /></label>)}<button className="admin-btn" type="button" onClick={() => setParams({})}>Сбросить</button></div>
    {error && <AdminError message={error} />}{loading ? <AdminLoading /> : !items.length ? <AdminEmpty message="Записей нет" /> : <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Дата</th><th>Уровень</th><th>Модуль</th><th>Сообщение</th><th>Связи</th></tr></thead><tbody>{items.map((row) => { const placeId = numericDetail(row.details, 'place_id'); const routeId = numericDetail(row.details, 'route_id'); return <tr key={row.id}><td>{new Date(row.created_at).toLocaleString('ru-RU')}</td><td>{logLevelText(row.level)}</td><td><Link to={`/admin/system-logs?module=${encodeURIComponent(row.module)}`}>{row.module}</Link></td><td>{row.message}{row.details && <details><summary>Структурированные детали</summary><pre>{JSON.stringify(row.details, null, 2)}</pre></details>}</td><td className="admin-actions-cell">{row.request_id && <Link className="admin-btn admin-btn-sm" to={`/admin/system-logs?request_id=${encodeURIComponent(row.request_id)}`}>Цепочка {row.request_id}</Link>}{row.city_slug && <Link className="admin-btn admin-btn-sm" to={`/admin/cities/${row.city_slug}`}>{row.city_slug}</Link>}{placeId && <Link className="admin-btn admin-btn-sm" to={`/admin/places/${placeId}`}>Место #{placeId}</Link>}{routeId && <Link className="admin-btn admin-btn-sm" to={`/admin/routes/data-quality?route_id=${routeId}`}>Маршрут #{routeId}</Link>}</td></tr> })}</tbody></table></div>}
    <div className="admin-actions-cell"><button className="admin-btn" disabled={offset === 0} onClick={() => update('offset', String(Math.max(0, offset - 50)))}>Назад</button><button className="admin-btn" disabled={offset + items.length >= total} onClick={() => update('offset', String(offset + 50))}>Далее</button></div>
  </div>
}
const LABELS: Record<string, string> = { q: 'Поиск', module: 'Модуль', city_slug: 'Город', request_id: 'Request ID', place_id: 'ID места', route_id: 'ID маршрута', actor_id: 'Администратор', environment: 'Окружение' }
