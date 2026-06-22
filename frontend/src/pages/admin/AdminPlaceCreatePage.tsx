import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import { AdminCategorySelect } from './AdminCategorySelect'
import type { AdminCitiesResponse } from './adminTypes'
import { AdminError } from './shared/AdminStates'

const SOURCES = [
  { value: 'admin_manual', label: 'Ручной ввод' },
  { value: 'osm', label: 'OSM' },
  { value: 'import', label: 'Импорт' },
  { value: 'enrichment', label: 'Обогащение' },
]

type LookupCandidate = { title?: string; address?: string; lat?: number; lng?: number; source?: string; error?: string }
type LookupResponse = { candidates: LookupCandidate[]; similar_places: Array<{ id: number; title: string; match_reason: string }> }

export const AdminPlaceCreatePage = () => {
  const nav = useNavigate()
  const [cities, setCities] = useState<AdminCitiesResponse['items']>([])
  const [cityId, setCityId] = useState(0)
  const [query, setQuery] = useState('')
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState('attraction')
  const [source, setSource] = useState('admin_manual')
  const [address, setAddress] = useState('')
  const [lat, setLat] = useState('')
  const [lng, setLng] = useState('')
  const [advanced, setAdvanced] = useState(false)
  const [candidates, setCandidates] = useState<LookupCandidate[]>([])
  const [dupes, setDupes] = useState<LookupResponse['similar_places']>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    adminGet<AdminCitiesResponse>('/admin/cities?limit=100').then((r) => {
      setCities(r.items)
      if (r.items[0]) setCityId(r.items[0].id)
    })
  }, [])

  const search = async () => {
    setBusy(true)
    setError(null)
    try {
      const res = await adminPost<LookupResponse>('/admin/places/lookup', { city_id: cityId, title: query })
      setCandidates(res.candidates)
      setDupes(res.similar_places)
      const first = res.candidates.find((c) => c.lat && c.lng && !c.error)
      if (first) {
        setTitle(String(first.title || query))
        setAddress(String(first.address || ''))
        setLat(String(first.lat))
        setLng(String(first.lng))
      } else {
        setTitle(query)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка поиска')
    } finally { setBusy(false) }
  }

  const create = async () => {
    setBusy(true)
    setError(null)
    try {
      const dupeRes = await adminPost<{ items: typeof dupes }>('/admin/places/check-duplicates', {
        city_id: cityId, title, address: address || null,
        lat: lat ? Number(lat) : null, lng: lng ? Number(lng) : null,
      })
      setDupes(dupeRes.items)
      if (dupeRes.items.length && !window.confirm(`Найдено ${dupeRes.items.length} похожих мест. Всё равно создать?`)) return
      const created = await adminPost<{ id: number }>('/admin/places/create-draft', {
        city_id: cityId, title, category, source, address: address || null,
        lat: lat ? Number(lat) : null, lng: lng ? Number(lng) : null,
      })
      nav(`/admin/places/${created.id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка')
    } finally { setBusy(false) }
  }

  return (
    <div>
      <Link to="/admin/places" className="admin-muted">← К списку</Link>
      <h2 className="admin-page-title">Создать место</h2>
      <p className="admin-page-subtitle">Поиск по названию или адресу. Координаты подставляются автоматически.</p>
      <div className="admin-filters admin-filters-stack">
        <select value={cityId} onChange={(e) => setCityId(Number(e.target.value))}>
          {cities.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <input placeholder="Название или адрес для поиска *" value={query} onChange={(e) => setQuery(e.target.value)} />
        <button type="button" className="admin-btn" disabled={busy || !query} onClick={search}>Найти место</button>
      </div>
      {candidates.length > 0 && (
        <div className="admin-detail-panel">
          <h3>Найдено</h3>
          <ul>{candidates.map((c, i) => (
            <li key={i}>
              {c.error ? c.error : `${c.title} — ${c.address} (${c.lat}, ${c.lng})`}
              {!c.error && c.lat && (
                <button type="button" className="admin-btn admin-btn-sm" onClick={() => {
                  setTitle(String(c.title || query)); setAddress(String(c.address || ''))
                  setLat(String(c.lat)); setLng(String(c.lng))
                }}>Выбрать</button>
              )}
            </li>
          ))}</ul>
        </div>
      )}
      <div className="admin-filters admin-filters-stack">
        <input placeholder="Название *" value={title} onChange={(e) => setTitle(e.target.value)} />
        <AdminCategorySelect value={category} onChange={setCategory} />
        <select value={source} onChange={(e) => setSource(e.target.value)}>
          {SOURCES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
        <input placeholder="Адрес" value={address} onChange={(e) => setAddress(e.target.value)} />
        <button type="button" className="admin-btn admin-btn-muted" onClick={() => setAdvanced((v) => !v)}>
          {advanced ? 'Скрыть дополнительно' : 'Дополнительно (координаты)'}
        </button>
        {advanced && (
          <>
            <input placeholder="Широта" value={lat} onChange={(e) => setLat(e.target.value)} />
            <input placeholder="Долгота" value={lng} onChange={(e) => setLng(e.target.value)} />
          </>
        )}
        <button type="button" className="admin-btn admin-btn-primary" disabled={busy || !title} onClick={create}>
          Создать черновик
        </button>
      </div>
      {error && <AdminError message={error} />}
      {dupes.length > 0 && (
        <div className="admin-detail-panel">
          <h3>Похожие места</h3>
          <ul>{dupes.map((d) => (
            <li key={d.id}><Link to={`/admin/places/${d.id}`}>{d.title}</Link> — {d.match_reason}</li>
          ))}</ul>
        </div>
      )}
    </div>
  )
}
