import { useCallback, useEffect, useState } from 'react'
import { adminGet, adminPost } from './adminApi'
import type { HealthAlert, ServiceHealth } from './adminPlatformTypes'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

const STATUS_LABELS: Record<string, string> = {
  acknowledged: 'Принят',
  open: 'Открыт',
  resolved: 'Закрыт',
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
    <h2 className="admin-page-title">Состояние системы</h2><p className="admin-page-subtitle">Сервисы, очереди и инциденты. Срок хранения журналов: 30 дней.</p>
    {error && <AdminError message={error} />}{loading ? <AdminLoading /> : <><div className="admin-action-grid">{services.map((row) => <div className={`admin-action-card admin-severity-${row.status === 'error' ? 'red' : row.status === 'warning' ? 'yellow' : 'green'}`} key={row.name}><strong>{row.name}</strong><p>{row.description}</p><span>Очередь: {row.queue_depth}</span>{row.latency_ms != null && <span>Задержка: {row.latency_ms} мс</span>}</div>)}</div><h3>Инциденты</h3>{!alerts.length ? <AdminEmpty message="Открытых инцидентов нет" /> : <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Время</th><th>Модуль</th><th>Проблема</th><th>Статус</th><th>Действия</th></tr></thead><tbody>{alerts.map((row) => <tr key={row.id}><td>{new Date(row.created_at).toLocaleString('ru-RU')}</td><td>{row.module}</td><td>{row.message}</td><td>{STATUS_LABELS[row.status] ?? 'Неизвестен'}</td><td><button className="admin-btn" disabled={busy === row.id || row.status === 'acknowledged'} onClick={() => void transition(row.id, 'acknowledged')}>Принять</button><button className="admin-btn" disabled={busy === row.id || row.status === 'resolved'} onClick={() => void transition(row.id, 'resolved')}>Закрыть</button>{row.status === 'resolved' && <button className="admin-btn" disabled={busy === row.id} onClick={() => void transition(row.id, 'open')}>Открыть снова</button>}</td></tr>)}</tbody></table></div>}</>}
  </div>
}
