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
          <td><input aria-label={`Выбрать ${row.title}`} type="checkbox" checked={selected.has(row.place_id)} onChange={() => onToggle(row.place_id)} /></td>
          <td><Link to={`/admin/places/${row.place_id}`}>{row.title}</Link></td>
          <td>{categoryText(row.category)}</td>
          <td>{row.eligible ? 'готово' : 'нужно исправить'}</td>
          <td>{row.quality_score} · {qualityText(row.quality_bucket)}</td>
          <td>{routeReasonText(row.primary_reason)}</td>
        </tr>)}
      </tbody>
    </table>
  )
}
