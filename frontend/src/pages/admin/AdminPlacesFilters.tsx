import type { AdminCity } from './adminTypes'
import { PLACE_PRESETS, PUB_STATUS_OPTIONS, VERIFY_STATUS_OPTIONS } from './adminPlacesPresets'
import { AdminCategorySelect } from './AdminCategorySelect'
import type { PlacesListFilters } from './useAdminPlacesList'

type Props = {
  cities: AdminCity[]
  value: PlacesListFilters
  expanded: boolean
  onChange: (changes: Partial<PlacesListFilters>) => void
  onToggleExpanded: () => void
  onReset: () => void
}

const presenceOptions = (allLabel: string) => <><option value="">{allLabel}</option><option value="true">Есть</option><option value="false">Нет</option></>

export const AdminPlacesFilters = ({ cities, value, expanded, onChange, onToggleExpanded, onReset }: Props) => (
  <section className="admin-filter-card">
    <div className="admin-filter-header">
      <div><div className="admin-help-title">Фильтры каталога</div><p className="admin-bulk-hint">Фильтры сохраняются в адресе страницы и не пропадают после возврата.</p></div>
      <button type="button" className="admin-btn admin-btn-muted" onClick={onToggleExpanded}>{expanded ? 'Скрыть дополнительные' : 'Все фильтры'}</button>
    </div>
    <div className="admin-filter-grid">
      <label className="admin-field admin-field-wide"><span>Поиск</span><input placeholder="Название, адрес, slug или ID" value={value.q} onChange={(event) => onChange({ q: event.target.value })} /></label>
      <label className="admin-field"><span>Город</span><select value={value.citySlug} onChange={(event) => onChange({ citySlug: event.target.value })}><option value="">Все города</option>{cities.map((city) => <option key={city.id} value={city.slug}>{city.name}</option>)}</select></label>
      <label className="admin-field"><span>Направление</span><input placeholder="slug направления" value={value.destinationSlug} onChange={(event) => onChange({ destinationSlug: event.target.value })} /></label>
      <label className="admin-field"><span>Быстрая выборка</span><select value={value.preset} onChange={(event) => onChange({ preset: event.target.value })}>{PLACE_PRESETS.map((item) => <option key={item.id || 'all'} value={item.id}>{item.label}</option>)}</select></label>
      <div className="admin-field"><span>Категория</span><AdminCategorySelect value={value.category} onChange={(category) => onChange({ category })} includeAll citySlug={value.citySlug} /></div>
      <label className="admin-field"><span>Публикация</span><select value={value.pubStatus} onChange={(event) => onChange({ pubStatus: event.target.value })}>{PUB_STATUS_OPTIONS.map((item) => <option key={item.value || 'any'} value={item.value}>{item.label}</option>)}</select></label>
      <label className="admin-field"><span>Проверка</span><select value={value.verifyStatus} onChange={(event) => onChange({ verifyStatus: event.target.value })}>{VERIFY_STATUS_OPTIONS.map((item) => <option key={item.value || 'any'} value={item.value}>{item.label}</option>)}</select></label>
      <label className="admin-field"><span>Маршруты</span><select value={value.routeEligible} onChange={(event) => onChange({ routeEligible: event.target.value })}><option value="">Все</option><option value="true">Допущены</option><option value="false">Исключены</option></select></label>
      <label className="admin-field"><span>Сортировка</span><select value={`${value.sort}:${value.direction}`} onChange={(event) => { const [sort, direction] = event.target.value.split(':'); onChange({ sort, direction }) }}><option value="updated:desc">Недавно изменённые</option><option value="created:desc">Недавно созданные</option><option value="title:asc">По названию</option><option value="quality:asc">Сначала низкое качество</option><option value="quality:desc">Сначала высокое качество</option><option value="confidence:asc">Сначала низкая уверенность</option><option value="id:desc">Сначала новые ID</option></select></label>
    </div>

    {expanded && <div className="admin-filter-grid admin-filter-grid-secondary">
      <label className="admin-field"><span>Фото</span><select value={value.hasPhoto} onChange={(event) => onChange({ hasPhoto: event.target.value })}>{presenceOptions('Фото: не важно')}</select></label>
      <label className="admin-field"><span>Адрес</span><select value={value.hasAddress} onChange={(event) => onChange({ hasAddress: event.target.value })}>{presenceOptions('Адрес: не важно')}</select></label>
      <label className="admin-field"><span>Описание</span><select value={value.hasDescription} onChange={(event) => onChange({ hasDescription: event.target.value })}>{presenceOptions('Описание: не важно')}</select></label>
      <label className="admin-field"><span>Телефон</span><select value={value.hasPhone} onChange={(event) => onChange({ hasPhone: event.target.value })}>{presenceOptions('Телефон: не важно')}</select></label>
      <label className="admin-field"><span>Сайт</span><select value={value.hasWebsite} onChange={(event) => onChange({ hasWebsite: event.target.value })}>{presenceOptions('Сайт: не важно')}</select></label>
      <label className="admin-field"><span>Часы работы</span><select value={value.hasHours} onChange={(event) => onChange({ hasHours: event.target.value })}>{presenceOptions('Часы: не важно')}</select></label>
      <label className="admin-field"><span>Активность</span><select value={value.active} onChange={(event) => onChange({ active: event.target.value })}><option value="">Все</option><option value="true">Активные</option><option value="false">Неактивные</option></select></label>
      <label className="admin-field"><span>Поиск</span><select value={value.searchable} onChange={(event) => onChange({ searchable: event.target.value })}><option value="">Все</option><option value="true">Доступны в поиске</option><option value="false">Скрыты из поиска</option></select></label>
      <label className="admin-field"><span>Качество</span><select value={value.qualityTier} onChange={(event) => onChange({ qualityTier: event.target.value })}><option value="">Любое</option><option value="gold">Отличное</option><option value="silver">Хорошее</option><option value="bronze">Требует улучшения</option><option value="draft">Черновое</option><option value="rejected">Отклонённое</option></select></label>
      <label className="admin-field"><span>Уверенность</span><select value={value.lowConfidence} onChange={(event) => onChange({ lowConfidence: event.target.value })}><option value="">Любая</option><option value="true">Только низкая</option></select></label>
      <label className="admin-field"><span>Источник</span><select value={value.source} onChange={(event) => onChange({ source: event.target.value })}><option value="">Все источники</option><option value="admin_manual">Ручной ввод</option><option value="osm">OpenStreetMap</option><option value="import">Импорт</option><option value="geoapify">Geoapify</option><option value="wikidata">Wikidata</option><option value="official_site">Официальный сайт</option></select></label>
      <label className="admin-field"><span>За один запрос</span><select value={value.limit} onChange={(event) => onChange({ limit: Number(event.target.value) })}><option value="20">20</option><option value="50">50</option><option value="100">100</option><option value="200">200</option></select></label>
    </div>}

    <div className="admin-filter-actions"><button type="button" className="admin-btn admin-btn-muted" onClick={onReset}>Сбросить всё</button></div>
  </section>
)
