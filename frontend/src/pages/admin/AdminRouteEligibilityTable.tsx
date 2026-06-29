import { Link } from 'react-router-dom'
import type { EligibilityRow } from './adminRouteTypes'
import { categoryText, qualityText, routeReasonText } from './adminRouteCopy'
import { AdminEmpty } from './shared/AdminStates'

type Props = {
  items: EligibilityRow[]
  selected: Set<number>
  onToggle: (placeId: number) => void
  onToggleAll: () => void
}

export const AdminRouteEligibilityTable = ({ items, selected, onToggle, onToggleAll }: Props) => {
  if (!items.length) return <AdminEmpty message="Нет мест" />
  const allVisibleSelected = items.every((row) => selected.has(row.place_id))
  return (
    <table className="admin-table">
      <thead>
        <tr>
          <th><input type="checkbox" aria-label="Выбрать все видимые места" checked={allVisibleSelected} onChange={onToggleAll} /></th>
          <th>Место</th>
          <th>Категория</th>
          <th>Готово</th>
          <th>Качество</th>
          <th>Что мешает</th>
        </tr>
      </thead>
      <tbody>
        {items.map((row) => <tr key={row.place_id}>
          <td data-label="Выбор"><input aria-label={`Выбрать ${row.title}`} type="checkbox" checked={selected.has(row.place_id)} onChange={() => onToggle(row.place_id)} /></td>
          <td data-label="Место">
            <Link to={`/admin/places/${row.place_id}`}>{row.title}</Link>
            {row.placeholder_name ? <div className="admin-muted">автоназвание, нужна проверка</div> : null}
          </td>
          <td data-label="Категория">{categoryText(row.category)}</td>
          <td data-label="Готово">{row.eligible ? 'готово' : 'нужно исправить'}</td>
          <td data-label="Качество">
            {row.quality_score} · {qualityText(row.quality_bucket)}
            {row.high_quality_route_candidate ? <div className="admin-muted">можно массово подтвердить</div> : null}
          </td>
          <td data-label="Что мешает">{routeReasonText(row.primary_reason)}</td>
        </tr>)}
      </tbody>
    </table>
  )
}
