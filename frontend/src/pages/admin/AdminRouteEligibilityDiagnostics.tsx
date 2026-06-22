import { Link } from 'react-router-dom'
import type { RouteReadinessDiagnostics, RouteReadinessPlace } from './adminRouteTypes'
import { categoryText, routeReasonText } from './adminRouteCopy'

export const AdminRouteEligibilityDiagnostics = ({ report }: { report: RouteReadinessDiagnostics }) => (
  <section className="admin-detail-panel">
    <h3>Готовность мест для маршрутов · {report.city_name}</h3>
    <div className="admin-metrics-grid admin-metrics-small">
      <Metric label="Всего мест" value={report.places_total} />
      <Metric label="Опубликовано" value={report.published_places} />
      <Metric label="Готово для маршрутов" value={report.eligible_places} />
      <Metric label="Нужно исправить" value={report.places_total - report.eligible_places} />
    </div>
    <BlockersTable counts={report.blockers_count_by_reason} />
    <PlacesTable title="Почти готовы" items={report.near_ready_places} empty="Нет мест с 1-2 проблемами" />
    <PlacesTable title="Примеры заблокированных" items={report.sample_blocked_places} empty="Нет заблокированных мест" />
  </section>
)

const Metric = ({ label, value }: { label: string; value: number }) => (
  <div className="admin-metric-card"><div className="admin-metric-value">{value}</div><div className="admin-metric-label">{label}</div></div>
)

const BlockersTable = ({ counts }: { counts: Record<string, number> }) => (
  <table className="admin-table">
    <thead><tr><th>Что мешает</th><th>Сколько мест</th></tr></thead>
    <tbody>{Object.entries(counts).map(([reason, count]) => <tr key={reason}><td>{routeReasonText(reason)}</td><td>{count}</td></tr>)}</tbody>
  </table>
)

const PlacesTable = ({ title, items, empty }: { title: string; items: RouteReadinessPlace[]; empty: string }) => (
  <div>
    <h3>{title}</h3>
    {!items.length ? <p className="admin-muted">{empty}</p> : (
      <table className="admin-table">
        <thead><tr><th>Место</th><th>Категория</th><th>Качество</th><th>Что мешает</th></tr></thead>
        <tbody>{items.map((place) => (
          <tr key={place.place_id}>
            <td><Link to={`/admin/places/${place.place_id}`}>{place.title}</Link></td>
            <td>{categoryText(place.category)}</td>
            <td>{place.quality_score}</td>
            <td>{place.blockers.map(routeReasonText).join(', ') || '—'}</td>
          </tr>
        ))}</tbody>
      </table>
    )}
  </div>
)
