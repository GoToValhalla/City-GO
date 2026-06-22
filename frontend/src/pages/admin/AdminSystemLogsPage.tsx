import { useCallback, useEffect, useState } from 'react'
import { adminGet } from './adminApi'
import { logLevelText } from './adminHumanText'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

type Log = {
  id: number; level: string; module: string; message: string
  details: Record<string, unknown> | null; city_slug: string | null
  request_id: string | null; created_at: string
}

export const AdminSystemLogsPage = () => {
  const [items, setItems] = useState<Log[]>([])
  const [total, setTotal] = useState(0)
  const [level, setLevel] = useState('')
  const [module, setModule] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    const sp = new URLSearchParams({ limit: '100' })
    if (level) sp.set('level', level)
    if (module) sp.set('module', module)
    adminGet<{ items: Log[]; total: number }>(`/admin/system-logs?${sp}`)
      .then((r) => { setItems(r.items); setTotal(r.total) })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [level, module])

  useEffect(() => { void Promise.resolve().then(load) }, [load])

  return (
    <div>
      <h2 className="admin-page-title">Системные логи ({total})</h2>
      <p className="admin-page-subtitle">Ошибки и события приложения.</p>
      <div className="admin-filters admin-filters-stack">
        <select value={level} onChange={(e) => setLevel(e.target.value)}>
          <option value="">Все уровни</option>
          {['info', 'warning', 'error', 'critical'].map((l) => <option key={l} value={l}>{logLevelText(l)}</option>)}
        </select>
        <input placeholder="Модуль" value={module} onChange={(e) => setModule(e.target.value)} />
        <button type="button" className="admin-btn admin-btn-primary" onClick={load}>Применить</button>
      </div>
      {error && <AdminError message={error} />}
      {loading ? <AdminLoading /> : items.length === 0 ? <AdminEmpty message="Записей нет" /> : (
        <div className="admin-table-wrap">
          <table className="admin-table admin-table-compact">
            <thead><tr><th>Дата</th><th>Уровень</th><th>Модуль</th><th>Сообщение</th></tr></thead>
            <tbody>
              {items.map((l) => (
                <tr key={l.id}>
                  <td>{new Date(l.created_at).toLocaleString('ru-RU')}</td>
                  <td><span className={`admin-badge pub-${l.level === 'error' || l.level === 'critical' ? 'hidden' : 'published'}`}>{logLevelText(l.level)}</span></td>
                  <td>{l.module}</td>
                  <td>{l.message}{l.details && <details className="admin-muted"><summary>Детали</summary><pre style={{ fontSize: 11 }}>{JSON.stringify(l.details, null, 2)}</pre></details>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
