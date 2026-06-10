import { Link } from 'react-router-dom'
import type { AdminPlace } from './adminTypes'

type Props = {
  items: AdminPlace[]
  busy: number | null
  selected: Set<number>
  onToggle: (id: number) => void
  onPublish: (id: number) => void
  onUnpublish: (id: number) => void
  onVerify: (id: number) => void
}

const flag = (v: boolean) => (v ? '✓' : '—')

export const AdminPlacesTable = ({ items, busy, selected, onToggle, onPublish, onUnpublish, onVerify }: Props) => (
  <div className="admin-table-wrap">
    <table className="admin-table">
      <thead>
        <tr>
          <th></th><th>ID</th><th>Название</th><th>Категория</th><th>Адрес</th>
          <th>Статус</th><th>Вериф.</th><th>Маршрут</th><th>Действия</th>
        </tr>
      </thead>
      <tbody>
        {items.map((p) => (
            <tr key={p.id}>
                <td><input type="checkbox" checked={selected.has(p.id)} onChange={() => onToggle(p.id)} /></td>
                <td>{p.id}</td>
                <td>
                  <Link to={`/admin/places/${p.id}`}><strong>{p.title}</strong></Link>
              <div className="admin-muted">{p.slug}</div>
            </td>
            <td>{p.category ?? '—'}</td>
            <td>{p.address ? '✓' : '—'}</td>
            <td><span className={`admin-badge pub-${p.publication_status}`}>{p.publication_status}</span></td>
            <td>{p.verification_status}</td>
            <td>{flag(p.is_route_eligible)}</td>
            <td className="admin-actions-cell">
              <button disabled={busy === p.id} onClick={() => onPublish(p.id)} className="admin-btn admin-btn-sm">Опубликовать</button>
              <button disabled={busy === p.id} onClick={() => onUnpublish(p.id)} className="admin-btn admin-btn-sm admin-btn-muted">Скрыть</button>
              <button disabled={busy === p.id} onClick={() => onVerify(p.id)} className="admin-btn admin-btn-sm admin-btn-ok">Верифицировать</button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
)
