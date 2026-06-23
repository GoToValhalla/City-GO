import { AdminCategorySelect } from './AdminCategorySelect'

export type AdminPlaceFormValue = {
  title: string
  category: string
  address: string
  lat: string
  lng: string
  shortDescription: string
  imageUrl: string
  website: string
  phone: string
  source: string
  sourceUrl: string
  atmosphere: string
  inside: string
  bestFor: string
  openingHours: string
  visitDuration: string
  priceLevel: string
  indoor: boolean
  outdoor: boolean
  dogFriendly: boolean
  familyFriendly: boolean
  isActive: boolean
  visibleToUsers: boolean
  searchable: boolean
  routeEnabled: boolean
  routeExclusionReason: string
  adminComment: string
}

type Props = {
  value: AdminPlaceFormValue
  onChange: (value: AdminPlaceFormValue) => void
  citySlug?: string
  showPublication?: boolean
  disabled?: boolean
}

const field = (value: AdminPlaceFormValue, onChange: Props['onChange'], key: keyof AdminPlaceFormValue, next: string | boolean) => {
  onChange({ ...value, [key]: next })
}

export const AdminPlaceForm = ({ value, onChange, citySlug, showPublication = false, disabled = false }: Props) => (
  <div className="admin-place-form">
    <section className="admin-form-section">
      <h3>Основная информация</h3>
      <div className="admin-form-grid">
        <label className="admin-field admin-field-wide">
          <span>Название *</span>
          <input disabled={disabled} value={value.title} onChange={(event) => field(value, onChange, 'title', event.target.value)} />
        </label>
        <label className="admin-field">
          <span>Категория *</span>
          <AdminCategorySelect value={value.category} onChange={(next) => field(value, onChange, 'category', next)} citySlug={citySlug} />
        </label>
        <label className="admin-field admin-field-wide">
          <span>Короткое описание</span>
          <textarea disabled={disabled} rows={3} value={value.shortDescription} onChange={(event) => field(value, onChange, 'shortDescription', event.target.value)} />
        </label>
        <label className="admin-field admin-field-wide">
          <span>Адрес</span>
          <input disabled={disabled} value={value.address} onChange={(event) => field(value, onChange, 'address', event.target.value)} />
        </label>
        <label className="admin-field">
          <span>Широта *</span>
          <input disabled={disabled} inputMode="decimal" value={value.lat} onChange={(event) => field(value, onChange, 'lat', event.target.value)} />
        </label>
        <label className="admin-field">
          <span>Долгота *</span>
          <input disabled={disabled} inputMode="decimal" value={value.lng} onChange={(event) => field(value, onChange, 'lng', event.target.value)} />
        </label>
      </div>
    </section>

    <section className="admin-form-section">
      <h3>Контакты и медиа</h3>
      <div className="admin-form-grid">
        <label className="admin-field admin-field-wide"><span>Фото</span><input disabled={disabled} type="url" placeholder="https://..." value={value.imageUrl} onChange={(event) => field(value, onChange, 'imageUrl', event.target.value)} /></label>
        <label className="admin-field"><span>Телефон</span><input disabled={disabled} type="tel" value={value.phone} onChange={(event) => field(value, onChange, 'phone', event.target.value)} /></label>
        <label className="admin-field"><span>Сайт</span><input disabled={disabled} type="url" placeholder="https://..." value={value.website} onChange={(event) => field(value, onChange, 'website', event.target.value)} /></label>
        <label className="admin-field"><span>Источник</span><select disabled={disabled} value={value.source} onChange={(event) => field(value, onChange, 'source', event.target.value)}><option value="admin_manual">Ручной ввод</option><option value="osm">OpenStreetMap</option><option value="import">Импорт</option><option value="enrichment">Обогащение</option><option value="official_site">Официальный сайт</option></select></label>
        <label className="admin-field"><span>Ссылка на источник</span><input disabled={disabled} type="url" placeholder="https://..." value={value.sourceUrl} onChange={(event) => field(value, onChange, 'sourceUrl', event.target.value)} /></label>
      </div>
    </section>

    <section className="admin-form-section">
      <h3>Содержание карточки</h3>
      <div className="admin-form-grid">
        <label className="admin-field admin-field-wide"><span>Атмосфера</span><textarea disabled={disabled} rows={2} value={value.atmosphere} onChange={(event) => field(value, onChange, 'atmosphere', event.target.value)} /></label>
        <label className="admin-field admin-field-wide"><span>Что внутри</span><textarea disabled={disabled} rows={2} value={value.inside} onChange={(event) => field(value, onChange, 'inside', event.target.value)} /></label>
        <label className="admin-field admin-field-wide"><span>Кому подойдёт</span><textarea disabled={disabled} rows={2} value={value.bestFor} onChange={(event) => field(value, onChange, 'bestFor', event.target.value)} /></label>
        <label className="admin-field admin-field-wide"><span>Часы работы</span><input disabled={disabled} placeholder="Пн-Вс 09:00-21:00" value={value.openingHours} onChange={(event) => field(value, onChange, 'openingHours', event.target.value)} /></label>
        <label className="admin-field"><span>Время посещения, минут</span><input disabled={disabled} type="number" min="1" max="1440" value={value.visitDuration} onChange={(event) => field(value, onChange, 'visitDuration', event.target.value)} /></label>
        <label className="admin-field"><span>Уровень цены</span><select disabled={disabled} value={value.priceLevel} onChange={(event) => field(value, onChange, 'priceLevel', event.target.value)}><option value="">Не указан</option><option value="1">Доступно</option><option value="2">Средний</option><option value="3">Выше среднего</option><option value="4">Дорого</option></select></label>
      </div>
      <div className="admin-check-grid">
        <label><input disabled={disabled} type="checkbox" checked={value.indoor} onChange={(event) => field(value, onChange, 'indoor', event.target.checked)} /> В помещении</label>
        <label><input disabled={disabled} type="checkbox" checked={value.outdoor} onChange={(event) => field(value, onChange, 'outdoor', event.target.checked)} /> На улице</label>
        <label><input disabled={disabled} type="checkbox" checked={value.familyFriendly} onChange={(event) => field(value, onChange, 'familyFriendly', event.target.checked)} /> Подходит семьям</label>
        <label><input disabled={disabled} type="checkbox" checked={value.dogFriendly} onChange={(event) => field(value, onChange, 'dogFriendly', event.target.checked)} /> Можно с собакой</label>
      </div>
    </section>

    {showPublication && (
      <section className="admin-form-section">
        <h3>Доступность</h3>
        <div className="admin-check-grid">
          <label><input disabled={disabled} type="checkbox" checked={value.isActive} onChange={(event) => field(value, onChange, 'isActive', event.target.checked)} /> Место активно</label>
          <label><input disabled={disabled} type="checkbox" checked={value.visibleToUsers} onChange={(event) => field(value, onChange, 'visibleToUsers', event.target.checked)} /> Видно в каталоге</label>
          <label><input disabled={disabled} type="checkbox" checked={value.searchable} onChange={(event) => field(value, onChange, 'searchable', event.target.checked)} /> Доступно в поиске</label>
          <label><input disabled={disabled} type="checkbox" checked={value.routeEnabled} onChange={(event) => field(value, onChange, 'routeEnabled', event.target.checked)} /> Можно добавлять в маршруты</label>
        </div>
        {!value.routeEnabled && <label className="admin-field"><span>Причина исключения из маршрутов</span><input disabled={disabled} value={value.routeExclusionReason} onChange={(event) => field(value, onChange, 'routeExclusionReason', event.target.value)} /></label>}
      </section>
    )}

    <section className="admin-form-section">
      <h3>Комментарий администратора</h3>
      <label className="admin-field"><textarea disabled={disabled} rows={3} value={value.adminComment} onChange={(event) => field(value, onChange, 'adminComment', event.target.value)} /></label>
    </section>
  </div>
)
