import { Link } from 'react-router-dom'
import type { EligibilityRow } from './adminRouteTypes'
import { AdminEmpty } from './shared/AdminStates'

type Props = {
  items: EligibilityRow[]
  selected: Set<number>
  onToggle: (placeId: number) => void
}

export const AdminRouteEligibilityTable = ({ items, selected, onToggle }: Props) => {
  if (!items.length) return <AdminEmpty message="Нет мест" />
  return (
    <table className="admin-table">
      <thead><tr><th /><th>Место</th><th>Категория</th><th>Eligible</th><th>Quality</th><th>Reason</th></tr></thead>
      <tbody>
        {items.map((row) => <tr key={row.place_id}>
          <td><input type="checkbox" checked={selected.has(row.place_id)} onChange={() => onToggle(row.place_id)} /></td>
          <td><Link to={`/admin/places/${row.place_id}`}>{row.title}</Link></td>
          <td>{row.category ?? '—'}</td>
          <td>{row.eligible ? '✓' : '✗'}</td>
          <td>{row.quality_score} ({row.quality_bucket})</td>
          <td>{row.primary_reason}</td>
        </tr>)}
      </tbody>
    </table>
  )
}
