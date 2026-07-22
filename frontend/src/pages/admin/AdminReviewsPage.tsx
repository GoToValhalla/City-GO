import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

type Review = { id: number; place_id: number; place_name: string; source: string | null; confidence: number | null; status: string; reason: string | null; created_at: string; place_version_at_creation: number }
type Diff = Review & { proposed_diff: Record<string, { current: unknown; proposed: unknown; reason?: string | null }> }
type SortKey = 'place' | 'source' | 'created'

const REASONS: Record<string, string> = {
  LOW_CONFIDENCE_SCORE: 'Низкая уверенность источника',
  MANUAL_OVERRIDE_PROTECTED: 'Поле защищено ручной правкой',
  SOURCE_PRIORITY_LOWER: 'Источник ниже по приоритету',
  VERSION_MISMATCH: 'Данные места изменились, обновите diff',
  VALUE_CONFLICT: 'Значение отличается от текущего',
}
const FIELDS: Record<string, string> = {
  title: 'Название', short_description: 'Описание', address: 'Адрес', category: 'Категория',
  canonical_category: 'Категория', lat: 'Широта', lng: 'Долгота', image_url: 'Фото',
  opening_hours: 'Часы работы', average_visit_duration_minutes: 'Время посещения',
}
const text = (value: unknown) => value == null || value === '' ? '—' : typeof value === 'object' ? JSON.stringify(value) : String(value)
const reasonText = (value?: string | null) => (value ?? '').split(',').map((item) => REASONS[item] ?? '').filter(Boolean).join(', ') || 'Требует проверки'

export const AdminReviewsPage = () => {
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const source = params.get('source') ?? ''
  const sortRaw = params.get('sort')
  const sort: SortKey = sortRaw === 'place' || sortRaw === 'source' || sortRaw === 'created' ? sortRaw : 'created'
  const dir = params.get('dir') === 'asc' ? 'asc' : 'desc'
  const [items, setItems] = useState<Review[]>([])
  const [diff, setDiff] = useState<Diff | null>(null)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [focusIndex, setFocusIndex] = useState(0)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setItems(await adminGet<Review[]>('/admin/reviews')) }
    catch { setError('Не удалось загрузить очередь слияния данных') }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase()
    const rows = items.filter((item) => {
      if (source && (item.source ?? '') !== source) return false
      if (!needle) return true
      return item.place_name.toLowerCase().includes(needle) || reasonText(item.reason).toLowerCase().includes(needle)
    })
    const factor = dir === 'asc' ? 1 : -1
    return [...rows].sort((a, b) => {
      if (sort === 'place') return a.place_name.localeCompare(b.place_name, 'ru') * factor
      if (sort === 'source') return (a.source ?? '').localeCompare(b.source ?? '', 'ru') * factor
      return (new Date(a.created_at).getTime() - new Date(b.created_at).getTime()) * factor
    })
  }, [items, q, source, sort, dir])

  const sources = useMemo(() => [...new Set(items.map((item) => item.source).filter(Boolean))] as string[], [items])

  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value); else next.delete(key)
    setParams(next, { replace: true })
  }
  const toggleSort = (key: SortKey) => {
    const next = new URLSearchParams(params)
    if (sort === key) next.set('dir', dir === 'asc' ? 'desc' : 'asc')
    else { next.set('sort', key); next.set('dir', key === 'created' ? 'desc' : 'asc') }
    setParams(next, { replace: true })
  }

  const open = async (id: number) => {
    setError(null); setNotice(null)
    try { const data = await adminGet<Diff>(`/admin/reviews/${id}/diff`); setDiff(data); setSelected(new Set()) }
    catch { setError('Не удалось открыть diff') }
  }
  const merge = async () => {
    if (!diff || selected.size === 0) return
    setBusy(true); setError(null)
    try {
      await adminPost(`/admin/reviews/${diff.id}/merge`, { fields_to_apply: [...selected], expected_version: diff.place_version_at_creation })
      setNotice('Выбранные поля применены'); setDiff(null); await load()
    } catch { setError('Данные места изменились или merge не применился. Обновите diff и повторите.') }
    finally { setBusy(false) }
  }
  const reject = async () => {
    if (!diff) return
    setBusy(true); setError(null)
    try { await adminPost(`/admin/reviews/${diff.id}/reject`, { reason: 'Отклонено оператором' }); setNotice('Заявка отклонена'); setDiff(null); await load() }
    catch { setError('Не удалось отклонить заявку') }
    finally { setBusy(false) }
  }
  const toggle = (field: string) => setSelected((current) => {
    const next = new Set(current)
    if (next.has(field)) next.delete(field); else next.add(field)
    return next
  })
  const selectAllFields = () => {
    if (!diff) return
    const keys = Object.keys(diff.proposed_diff)
    setSelected(selected.size === keys.length ? new Set() : new Set(keys))
  }

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLSelectElement) return
      if (!filtered.length) return
      if (event.key === 'j') { event.preventDefault(); setFocusIndex((i) => Math.min(filtered.length - 1, i + 1)) }
      if (event.key === 'k') { event.preventDefault(); setFocusIndex((i) => Math.max(0, i - 1)) }
      if (event.key === 'Enter') { event.preventDefault(); void open(filtered[focusIndex]?.id) }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [filtered, focusIndex])

  if (loading) return <AdminLoading />
  return <div>
    <header className="admin-page-header"><div><h1 className="admin-page-title">Слияние данных мест</h1><p className="admin-page-subtitle">Проверка изменений enrichment перед публикацией в карточках. j/k — строка, Enter — diff.</p></div></header>
    <section className="admin-filter-card admin-filter-grid admin-filters-sticky">
      <label className="admin-field"><span>Поиск</span><input value={q} onChange={(e) => setFilter('q', e.target.value)} placeholder="место или причина" /></label>
      <label className="admin-field"><span>Источник</span><select value={source} onChange={(e) => setFilter('source', e.target.value)}><option value="">Все</option>{sources.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
      <button type="button" className="admin-btn" onClick={() => setParams({}, { replace: true })}>Сбросить</button>
    </section>
    {notice && <p className="admin-success-text">{notice}</p>}{error && <AdminError message={error} />}
    {!filtered.length ? <AdminEmpty message="Заявок на слияние нет" /> : <section className="admin-section"><div className="admin-table-wrap"><table className="admin-table"><thead><tr>
      <th className="admin-sortable-th" aria-sort={sort === 'place' ? (dir === 'asc' ? 'ascending' : 'descending') : 'none'} onClick={() => toggleSort('place')}>Место</th>
      <th className="admin-sortable-th" aria-sort={sort === 'source' ? (dir === 'asc' ? 'ascending' : 'descending') : 'none'} onClick={() => toggleSort('source')}>Источник</th>
      <th>Причина</th>
      <th className="admin-sortable-th" aria-sort={sort === 'created' ? (dir === 'asc' ? 'ascending' : 'descending') : 'none'} onClick={() => toggleSort('created')}>Создано</th>
      <th /></tr></thead><tbody>{filtered.map((item, index) => <tr key={item.id} className={index === focusIndex ? 'admin-row-focused' : undefined}><td><Link to={`/admin/places/${item.place_id}`}>{item.place_name}</Link></td><td>{item.source ?? '—'} · {item.confidence != null ? `${Math.round(item.confidence * 100)}%` : '—'}</td><td>{reasonText(item.reason)}</td><td>{new Date(item.created_at).toLocaleString('ru-RU')}</td><td><button className="admin-btn admin-btn-sm" onClick={() => void open(item.id)}>Открыть diff</button></td></tr>)}</tbody></table></div></section>}
    {diff ? <section className="admin-detail-panel"><h2>Diff: {diff.place_name}</h2><div className="admin-actions-cell"><button type="button" className="admin-btn admin-btn-sm" onClick={selectAllFields}>{selected.size === Object.keys(diff.proposed_diff).length ? 'Снять все поля' : 'Выбрать все поля'}</button></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Применить</th><th>Поле</th><th>Сейчас</th><th>Предложено</th><th>Причина</th></tr></thead><tbody>{Object.entries(diff.proposed_diff).map(([field, row]) => <tr key={field}><td><input aria-label={`Выбрать ${FIELDS[field] ?? field}`} type="checkbox" checked={selected.has(field)} onChange={() => toggle(field)} /></td><td>{FIELDS[field] ?? field}</td><td>{text(row.current)}</td><td>{text(row.proposed)}</td><td>{reasonText(row.reason ?? diff.reason)}</td></tr>)}</tbody></table></div><div className="admin-bulk-bar-sticky"><button className="admin-btn admin-btn-primary" disabled={busy || selected.size === 0} onClick={() => void merge()}>{busy ? 'Применяем…' : 'Применить выбранное'}</button><button className="admin-btn admin-btn-danger" disabled={busy} onClick={() => void reject()}>Отклонить</button><button className="admin-btn" disabled={busy} onClick={() => void open(diff.id)}>Обновить diff</button></div></section> : null}
  </div>
}
