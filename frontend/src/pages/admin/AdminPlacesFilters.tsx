import type { AdminCity } from './adminTypes'
import { PLACE_PRESETS, PUB_STATUS_OPTIONS, VERIFY_STATUS_OPTIONS } from './adminPlacesPresets'
import { AdminCategorySelect } from './AdminCategorySelect'

type Props = {
  cities: AdminCity[]
  citySlug: string
  preset: string
  pubStatus: string
  verifyStatus: string
  category: string
  q: string
  onCityChange: (v: string) => void
  onPresetChange: (v: string) => void
  onPubStatusChange: (v: string) => void
  onVerifyStatusChange: (v: string) => void
  onCategoryChange: (v: string) => void
  onQChange: (v: string) => void
  onSearch: () => void
}

export const AdminPlacesFilters = (p: Props) => (
  <div className="admin-filters admin-filters-stack">
    <select value={p.citySlug} onChange={(e) => p.onCityChange(e.target.value)} aria-label="Город">
      <option value="">Все города</option>
      {p.cities.map((c) => <option key={c.id} value={c.slug}>{c.name}</option>)}
    </select>
    <select value={p.preset} onChange={(e) => p.onPresetChange(e.target.value)} aria-label="Пресет">
      {PLACE_PRESETS.map((x) => <option key={x.id || 'all'} value={x.id}>{x.label}</option>)}
    </select>
    <select value={p.pubStatus} onChange={(e) => p.onPubStatusChange(e.target.value)}>
      {PUB_STATUS_OPTIONS.map((x) => <option key={x.value || 'any'} value={x.value}>{x.label}</option>)}
    </select>
    <select value={p.verifyStatus} onChange={(e) => p.onVerifyStatusChange(e.target.value)}>
      {VERIFY_STATUS_OPTIONS.map((x) => <option key={x.value || 'any'} value={x.value}>{x.label}</option>)}
    </select>
    <AdminCategorySelect value={p.category} onChange={p.onCategoryChange} includeAll />
    <input placeholder="Поиск по названию" value={p.q} onChange={(e) => p.onQChange(e.target.value)} />
    <button type="button" className="admin-btn admin-btn-primary" onClick={p.onSearch}>Найти</button>
  </div>
)
