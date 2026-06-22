import { Link } from 'react-router-dom'
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

const routeFlag = (v: boolean) => (v ? 'да' : 'нет')

const AdminAddressCell = ({ place }: { place: AdminPlace }) => {
  const view = placeAddressView({
    address: place.address ?? '',
    category: place.category ?? '',
    lat: place.lat,
    lng: place.lng,
  })

  return (
    <div className={view.unclear ? 'admin-muted' : ''}>
      <span>{view.label}</span>
      {view.unclear && view.mapUrl ? (
        <div>
          <a href={view.mapUrl} target="_blank" rel="noopener noreferrer">Открыть на карте</a>
        </div>
      ) : null}
    </div>
  )
}

export const AdminPlacesTable = ({ items, busy, selected, onToggle, onToggleAll, onPublish, onUnpublish, onVerify }: Props) => {
  const allVisibleSelected = items.length > 0 && items.every((p) => selected.has(p.id))

  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <thead>
          <tr>
            <th><input type="checkbox" aria-label="Выбрать все видимые места" checked={allVisibleSelected} onChange={onToggleAll} /></th>
            <th>ID</th><th>Название</th><th>Категория</th><th>Адрес</th>
            <th>Публикация</th><th>Проверка</th><th>В маршруты</th><th>Действия</th>
          </tr>
        </thead>
        <tbody>
          {items.map((p) => (
              <tr key={p.id}>
                  <td><input type="checkbox" aria-label={`Выбрать ${p.title}`} checked={selected.has(p.id)} onChange={() => onToggle(p.id)} /></td>
                  <td>{p.id}</td>
                  <td>
                    <Link to={`/admin/places/${p.id}`}><strong>{p.title}</strong></Link>
                <div className="admin-muted">{p.slug}</div>
              </td>
              <td>{categoryText(p.category)}</td>
              <td><AdminAddressCell place={p} /></td>
              <td><span className={`admin-badge pub-${p.publication_status}`}>{publicationStatusText(p.publication_status)}</span></td>
              <td>{verificationStatusText(p.verification_status)}</td>
              <td>{routeFlag(p.is_route_eligible)}</td>
              <td className="admin-actions-cell">
                <button disabled={busy === p.id} onClick={() => onPublish(p.id)} className="admin-btn admin-btn-sm" title="Сделать место видимым на сайте">Опубликовать</button>
                <button disabled={busy === p.id} onClick={() => onUnpublish(p.id)} className="admin-btn admin-btn-sm admin-btn-muted" title="Скрыть место с сайта, но не удалить из базы">Скрыть с сайта</button>
                <button disabled={busy === p.id} onClick={() => onVerify(p.id)} className="admin-btn admin-btn-sm admin-btn-ok" title="Подтвердить, что место реально существует и данные можно использовать">Подтвердить</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
