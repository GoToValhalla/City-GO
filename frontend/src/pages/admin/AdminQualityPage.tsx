import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet } from './adminApi'
import type { QualityCity } from './adminPlatformTypes'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

export const AdminQualityPage = () => {
  const [params, setParams] = useSearchParams()
  const [items, setItems] = useState<QualityCity[]>([])
  const [todo, setTodo] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const load = useCallback(() => {
    setLoading(true); setError(null)
    adminGet<{ items: QualityCity[]; todo: string[] }>(`/admin/quality?${params}`)
      .then((row) => { setItems(row.items); setTodo(row.todo) })
      .catch((e: Error) => setError(e.message)).finally(() => setLoading(false))
  }, [params])
  useEffect(() => { void Promise.resolve().then(load) }, [load])
  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next)
  }
  return <div>
    <h2 className="admin-page-title">Качество данных</h2>
    <p className="admin-page-subtitle">Сводка качества данных по городам на основе текущих показателей.</p>
    <div className="admin-filter-card admin-filter-grid">
      <label className="admin-field"><span>Город</span><input value={params.get('city_slug') ?? ''} onChange={(e) => update('city_slug', e.target.value)} /></label>
      <label className="admin-field"><span>Регион</span><input value={params.get('region') ?? ''} onChange={(e) => update('region', e.target.value)} /></label>
      <label className="admin-field"><span>Категория</span><input value={params.get('category') ?? ''} onChange={(e) => update('category', e.target.value)} /></label>
      <label className="admin-field"><span>Важность</span><select value={params.get('severity') ?? ''} onChange={(e) => update('severity', e.target.value)}><option value="">Любая</option><option value="critical">Критично</option><option value="warning">Внимание</option><option value="ok">Норма</option></select></label>
    </div>
    {error && <AdminError message={error} />}{loading ? <AdminLoading /> : !items.length ? <AdminEmpty message="Нет данных по выбранным фильтрам" /> : <div className="admin-action-grid">{items.map((item) => <Link className={`admin-action-card admin-severity-${item.severity === 'critical' ? 'red' : item.severity === 'warning' ? 'yellow' : 'green'}`} to={`/admin/cities/${item.city_slug}?tab=quality`} key={item.city_slug}><strong>{item.city_name}</strong><div className="admin-action-count">{item.readiness_score}%</div><span>{item.places_total} мест</span></Link>)}</div>}
    <section className="admin-help-panel"><strong>Следующий этап</strong><ul>{todo.map((text) => <li key={text}>{text}</li>)}</ul></section>
  </div>
}
