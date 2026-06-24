import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import type { HealthAlert, ServiceHealth } from './adminPlatformTypes'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

const STATUS_LABELS: Record<string, string> = { acknowledged: 'Принят', open: 'Открыт', resolved: 'Закрыт' }
const logLink = (row: HealthAlert) => {
  const query = new URLSearchParams({ module: row.module })
  if (row.request_id) query.set('request_id', row.request_id)
  if (row.city_slug) query.set('city_slug', row.city_slug)
  return `/admin/system-logs?${query}`
}

export const AdminSystemHealthPage = () => {
  const [services, setServices] = useState<ServiceHealth[]>([])
  const [alerts, setAlerts] = useState<HealthAlert[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<number | null>(null)
  const load = useCallback(() => {
    setLoading(true)
    Promise.all([adminGet<{ services: ServiceHealth[] }>('/admin/system-health'), adminGet<{ items: HealthAlert[] }>('/admin/system-health/alerts')])
      .then(([health, alertRows]) => { setServices(health.services); setAlerts(alertRows.items) })
      .catch((e: Error) => setError(e.message)).finally(() => setLoading(false))
  }, [])
  useEffect(() => { void Promise.resolve().then(load) }, [load])
  const transition = async (id: number, status: string) => {
    setBusy(id)
    try { await adminPost(`/admin/system-health/alerts/${id}`, { status }); load() }
    catch (e) { setError(e instanceof Error ? e.message : 'Не удалось изменить инцидент') }
    finally { setBusy(null) }
  }
  return <div>
    <h2 className="admin-page-title">Состояние системы</h2><p className="admin-page-subtitle">Нажатие на сервис или инцидент открывает связанные логи и correlation chain.</p>
    {error && <AdminError message={error} />}{loading ? <AdminLoading /> : <><div className="admin-action-grid">{services.map((row) => <Link to={`/admin/system-logs?module=${encodeURIComponent(row.name)}`} className={`admin-action-card admin-severity-${row.status === 'error' ? 'red' : row.status === 'warning' ? 'yellow' : 'green'}`} key={row.name}><strong>{row.name}</strong><p>{row.description}</p><span>Очередь: {row.queue_depth}</span>{row.latency_ms != null && <span>Задержка: {row.latency_ms} мс</span>}<span className="admin-muted">Открыть логи →</span></Link>)}</div><h3>Инциденты</h3>{!alerts.length ? <AdminEmpty message="Открытых инцидентов нет" /> : <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Время</th><th>Модуль</th><th>Проблема</th><th>Статус</th><th>Действия</th></tr></thead><tbody>{alerts.map((row) => <tr key={row.id}><td><Link to={logLink(row)}>{new Date(row.created_at).toLocaleString('ru-RU')}</Link></td><td><Link to={logLink(row)}>{row.module}</Link></td><td><Link to={logLink(row)}>{row.message}</Link></td><td>{STATUS_LABELS[row.status] ?? 'Неизвестен'}</td><td><Link className="admin-btn" to={logLink(row)}>Расследовать</Link><button className="admin-btn" disabled={busy === row.id || row.status === 'acknowledged'} onClick={() => void transition(row.id, 'acknowledged')}>Принять</button><button className="admin-btn" disabled={busy === row.id || row.status === 'resolved'} onClick={() => void transition(row.id, 'resolved')}>Закрыть</button>{row.status === 'resolved' && <button className="admin-btn" disabled={busy === row.id} onClick={() => void transition(row.id, 'open')}>Открыть снова</button>}</td></tr>)}</tbody></table></div>}</>}
  </div>
}
