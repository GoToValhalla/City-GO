import { useState } from 'react'
import { Link } from 'react-router-dom'
import { adminPost } from './adminApi'
import type { AdminCityImportResponse } from './adminTypes'

const PIPELINE_STEPS = [
  'Создание города',
  'Постановка import job',
  'Сбор мест из источников',
  'Сохранение мест',
  'Очередь адресов и фото',
  'Data Quality report',
  'City Readiness',
]

type Props = { onCreated: () => void }

export const AdminCityCreateForm = ({ onCreated }: Props) => {
  const [name, setName] = useState('')
  const [region, setRegion] = useState('')
  const [country, setCountry] = useState('Россия')
  const [timezone, setTimezone] = useState('Europe/Kaliningrad')
  const [radiusKm, setRadiusKm] = useState('15')
  const [result, setResult] = useState<AdminCityImportResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async () => {
    const trimmed = name.trim()
    if (!trimmed) {
      setError('Укажите название города')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const payload = await adminPost<AdminCityImportResponse>('/admin/cities/import', {
        name: trimmed,
        region: region.trim() || null,
        country: country.trim() || 'Россия',
        timezone: timezone.trim() || 'Europe/Kaliningrad',
        radius_km: Number(radiusKm) || 15,
      })
      setResult(payload)
      setName('')
      onCreated()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка создания города')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="admin-detail-panel admin-city-create">
      <h3>Добавить город и запустить сбор данных</h3>
      <p className="admin-muted">Админ вводит город, система создаёт запись и ставит автоматический pipeline сбора/импорта в очередь.</p>
      <div className="admin-form-grid">
        <label>Название<input value={name} onChange={(e) => setName(e.target.value)} placeholder="Алматы" /></label>
        <label>Регион<input value={region} onChange={(e) => setRegion(e.target.value)} placeholder="Алматинская область" /></label>
        <label>Страна<input value={country} onChange={(e) => setCountry(e.target.value)} /></label>
        <label>Часовой пояс<input value={timezone} onChange={(e) => setTimezone(e.target.value)} placeholder="Asia/Almaty" /></label>
        <label>Радиус сбора, км<input type="number" min={1} max={200} value={radiusKm} onChange={(e) => setRadiusKm(e.target.value)} /></label>
      </div>
      <ol className="admin-muted">
        {PIPELINE_STEPS.map((step) => <li key={step}>{step}</li>)}
      </ol>
      {error && <p className="admin-error-text">{error}</p>}
      {result && (
        <div className="admin-card">
          <strong>{result.message}</strong>
          <p className="admin-muted">Slug: <strong>{result.city_slug}</strong>. {result.next_step}</p>
          <div className="admin-filters admin-filters-stack">
            <Link className="admin-btn admin-btn-sm" to="/admin/imports">Импорты</Link>
            <Link className="admin-btn admin-btn-sm" to={`/admin/routes/data-quality?city=${result.city_slug}`}>Data Quality</Link>
            <Link className="admin-btn admin-btn-sm" to={`/admin/routes/readiness/${result.city_slug}`}>Readiness</Link>
          </div>
        </div>
      )}
      <button type="button" className="admin-btn" disabled={busy} onClick={submit}>
        {busy ? 'Создание…' : 'Создать город и собрать места'}
      </button>
    </div>
  )
}
