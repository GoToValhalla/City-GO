import { Link } from 'react-router-dom'
import { adminPut } from './adminApi'

type CityToggle = { key: string; label?: string | null; value_bool: boolean }
export type CitySettings = { city_slug: string; city_name: string; toggles: CityToggle[] }

const QUICK_KEYS = [
  'city_visible_to_users', 'route_generation_enabled', 'web_enabled', 'telegram_enabled',
  'ai_recommendations_enabled', 'import_enabled', 'verified_places_only',
  'hide_without_photo', 'hide_without_address', 'hide_low_quality',
]

type Props = {
  settings: CitySettings
  busy: string | null
  onClose: () => void
  onRefresh: (slug: string) => void
  onError: (message: string) => void
}

export const AdminCitySettingsPanel = ({ settings, busy, onClose, onRefresh, onError }: Props) => {
  const toggle = async (key: string, next: boolean) => {
    if (!window.confirm(`Изменить настройку «${key}»?`)) return
    try {
      await adminPut(`/admin/cities/${settings.city_slug}/settings/${key}`, { value_bool: next, reason: 'inline cities' })
      onRefresh(settings.city_slug)
    } catch (e) {
      onError(e instanceof Error ? e.message : 'Ошибка')
    }
  }

  return (
    <div className="admin-detail-panel">
      <h3>Настройки: {settings.city_name}</h3>
      <div className="admin-toggle-list">
        {settings.toggles.filter((t) => QUICK_KEYS.includes(t.key)).map((t) => (
          <label key={t.key} className="admin-toggle-row">
            <input type="checkbox" checked={t.value_bool} disabled={busy === t.key}
              onChange={(e) => toggle(t.key, e.target.checked)} />
            <span><strong>{t.label ?? t.key}</strong></span>
          </label>
        ))}
      </div>
      <Link className="admin-btn admin-btn-sm" to={`/admin/features?scope=city&city=${settings.city_slug}`}>Все настройки</Link>
      <button type="button" className="admin-btn admin-btn-sm admin-btn-muted" onClick={onClose}>Закрыть</button>
    </div>
  )
}
