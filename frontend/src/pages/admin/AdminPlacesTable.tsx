import { Link, useLocation } from 'react-router-dom'
import { placeAddressView } from '../../shared/place/placeAddress'
import { categoryText } from './adminRouteCopy'
import { publicationStatusText, verificationStatusText } from './adminHumanText'
import type { AdminPlace } from './adminTypes'

type Props = {
  items: AdminPlace[]
  busy: number | null
  selected: Set<number>
  onToggle: (id: number) => void
  onToggleAll: () => void
  onPublish: (id: number) => void
  onUnpublish: (id: number) => void
  onVerify: (id: number) => void
}

const technicalOsmLabel = /^(?:osm[\s:_-]*)?(?:node|way|relation)[\s:_-]*\d+$/i
const displayPlaceTitle = (place: AdminPlace) => technicalOsmLabel.test(place.title.trim()) ? 'Без названия' : place.title

const AdminAddressCell = ({ place }: { place: AdminPlace }) => {
  const view = placeAddressView({ address: place.address ?? '', category: place.category ?? '', lat: place.lat, lng: place.lng })
  return <div className={view.unclear ? 'admin-muted' : ''}><span>{view.label}</span>{view.unclear && view.mapUrl && <div><a href={view.mapUrl} target="_blank" rel="noopener noreferrer">Открыть на карте</a></div>}</div>
}

export const AdminPlacesTable = ({ items, busy, selected, onToggle, onToggleAll, onPublish, onUnpublish, onVerify }: Props) => {
  const location = useLocation()
  const allVisibleSelected = items.length > 0 && items.every((place) => selected.has(place.id))
  const returnPath = `${location.pathname}${location.search}`

  return (
    <div className="admin-table-wrap">
      <table className="admin-table admin-responsive-table">
        <thead><tr><th><input type="checkbox" aria-label="Выбрать все загруженные места" checked={allVisibleSelected} onChange={onToggleAll} /></th><th>ID</th><th>Название</th><th>Категория</th><th>Адрес</th><th>Публикация</th><th>Проверка</th><th>Маршруты</th><th>Действия</th></tr></thead>
        <tbody>{items.map((place) => (
          <tr key={place.id} className={selected.has(place.id) ? 'admin-row-selected' : ''}>
            <td data-label="Выбор"><input type="checkbox" aria-label={`Выбрать место ${place.id}`} checked={selected.has(place.id)} onChange={() => onToggle(place.id)} /></td>
            <td data-label="ID">{place.id}</td>
            <td data-label="Название"><Link to={`/admin/places/${place.id}?from=${encodeURIComponent(returnPath)}`}><strong>{displayPlaceTitle(place)}</strong></Link></td>
            <td data-label="Категория">{categoryText(place.category)}</td>
            <td data-label="Адрес"><AdminAddressCell place={place} /></td>
            <td data-label="Публикация"><span className={`admin-badge pub-${place.publication_status}`}>{publicationStatusText(place.publication_status)}</span></td>
            <td data-label="Проверка">{verificationStatusText(place.verification_status)}</td>
            <td data-label="Маршруты">{place.is_route_eligible ? 'Да' : 'Нет'}</td>
            <td data-label="Действия" className="admin-actions-cell">
              <Link className="admin-btn admin-btn-sm" to={`/admin/places/${place.id}?from=${encodeURIComponent(returnPath)}`}>Открыть</Link>
              {place.publication_status !== 'published' && <button disabled={busy === place.id} onClick={() => onPublish(place.id)} className="admin-btn admin-btn-sm">Опубликовать</button>}
              {place.publication_status === 'published' && <button disabled={busy === place.id} onClick={() => onUnpublish(place.id)} className="admin-btn admin-btn-sm admin-btn-danger">Скрыть</button>}
              {place.verification_status !== 'verified' && <button disabled={busy === place.id} onClick={() => onVerify(place.id)} className="admin-btn admin-btn-sm admin-btn-ok">Подтвердить</button>}
            </td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  )
}
