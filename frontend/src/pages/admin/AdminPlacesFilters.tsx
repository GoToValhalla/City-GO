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
  routeEligible: string
  q: string
  onCityChange: (v: string) => void
  onPresetChange: (v: string) => void
  onPubStatusChange: (v: string) => void
  onVerifyStatusChange: (v: string) => void
  onCategoryChange: (v: string) => void
  onRouteEligibleChange: (v: string) => void
  onQChange: (v: string) => void
  onSearch: () => void
  onReset: () => void
}

export const AdminPlacesFilters = (p: Props) => (
  <section className="admin-filter-card">
    <div className="admin-help-title">Фильтры мест</div>
    <p className="admin-bulk-hint">Сначала сузьте список, затем выберите видимые места и примените массовое действие.</p>
    <div className="admin-filters admin-filters-stack">
      <select value={p.citySlug} onChange={(e) => p.onCityChange(e.target.value)} aria-label="Город">
        <option value="">Все города</option>
        {p.cities.map((c) => <option key={c.id} value={c.slug}>{c.name}</option>)}
      </select>
      <select value={p.preset} onChange={(e) => p.onPresetChange(e.target.value)} aria-label="Быстрый фильтр">
        {PLACE_PRESETS.map((x) => <option key={x.id || 'all'} value={x.id}>{x.label}</option>)}
      </select>
      <select value={p.pubStatus} onChange={(e) => p.onPubStatusChange(e.target.value)} aria-label="Статус публикации">
        {PUB_STATUS_OPTIONS.map((x) => <option key={x.value || 'any'} value={x.value}>{x.label}</option>)}
      </select>
      <select value={p.verifyStatus} onChange={(e) => p.onVerifyStatusChange(e.target.value)} aria-label="Статус проверки">
        {VERIFY_STATUS_OPTIONS.map((x) => <option key={x.value || 'any'} value={x.value}>{x.label}</option>)}
      </select>
      <select value={p.routeEligible} onChange={(e) => p.onRouteEligibleChange(e.target.value)} aria-label="Фильтр маршрутов">
        <option value="">Маршруты: все</option>
        <option value="true">Только в маршрутах</option>
        <option value="false">Исключены из маршрутов</option>
      </select>
      <AdminCategorySelect value={p.category} onChange={p.onCategoryChange} includeAll citySlug={p.citySlug} />
      <input placeholder="Поиск по названию, адресу или slug" value={p.q} onChange={(e) => p.onQChange(e.target.value)} />
      <button type="button" className="admin-btn admin-btn-primary" onClick={p.onSearch}>Применить фильтры</button>
      <button type="button" className="admin-btn admin-btn-sm" onClick={p.onReset}>Сбросить</button>
    </div>
  </section>
)
