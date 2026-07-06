import { useCallback, useEffect, useState } from 'react'
import { adminGet } from './adminApi'
import { AdminLoading, AdminSectionError } from './shared/AdminStates'

type DebugReport = {
  id: number
  public_id: string
  created_at: string
  screen: string
  severity: string
  category: string
  city_slug?: string | null
  request_id?: string | null
  title: string
  summary: string
  telegram_sent: boolean
  sanitized_payload: Record<string, unknown>
}

export const AdminDebugReportsPage = () => {
  const [items, setItems] = useState<DebugReport[]>([])
  const [selected, setSelected] = useState<DebugReport | null>(null)
  const [city, setCity] = useState('')
  const [requestId, setRequestId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (city) params.set('city_slug', city)
      if (requestId) params.set('request_id', requestId)
      const data = await adminGet<{ items: DebugReport[] }>(`/admin/debug-reports?${params.toString()}`)
      setItems(data.items)
      setSelected(data.items[0] ?? null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось загрузить отчёты')
    } finally {
      setLoading(false)
    }
  }, [city, requestId])

  useEffect(() => { void load() }, [load])

  if (loading) return <AdminLoading message="Загрузка отчётов диагностики…" />
  if (error) return <AdminSectionError title="Ошибка" message={error} onRetry={() => void load()} />

  return <div className="admin-page">
    <header className="admin-page-header"><div><h1 className="admin-page-title">Отчёты диагностики</h1><p className="admin-page-subtitle">Полные диагностические отчёты с телефона и публичного сайта.</p></div></header>
    <section className="admin-section">
      <div className="admin-filter-grid">
        <label className="admin-field"><span>Город</span><input value={city} onChange={(event) => setCity(event.target.value)} /></label>
        <label className="admin-field"><span>ID запроса</span><input value={requestId} onChange={(event) => setRequestId(event.target.value)} /></label>
        <button type="button" className="admin-btn" onClick={() => void load()}>Найти</button>
      </div>
    </section>
    <section className="admin-section">
      <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>ID</th><th>Экран</th><th>Город</th><th>Сводка</th><th>Telegram</th></tr></thead><tbody>
        {items.map((item) => <tr key={item.id} onClick={() => setSelected(item)}><td>{item.public_id}</td><td>{item.screen}</td><td>{item.city_slug ?? '-'}</td><td>{item.summary}</td><td>{item.telegram_sent ? 'Да' : 'Нет'}</td></tr>)}
        {!items.length ? <tr><td colSpan={5}>Отчётов пока нет</td></tr> : null}
      </tbody></table></div>
    </section>
    {selected ? <section className="admin-section"><h2 className="admin-section-title">{selected.title}</h2><p>{selected.summary}</p><p className="admin-page-subtitle">ID запроса: {selected.request_id ?? '-'} · Важность: {selected.severity} · Категория: {selected.category}</p><details><summary>Полная очищенная диагностика</summary><pre>{JSON.stringify(selected.sanitized_payload, null, 2)}</pre></details></section> : null}
  </div>
}
