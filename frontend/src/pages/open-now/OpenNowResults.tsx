import { PlaceList } from '../../components/places'
import type { OpenNowPlace } from '../../api/open-now/openNow.api'
import { DiagnosticsPanel } from '../../shared/debug/DiagnosticsPanel'

type Props = {
  error: string | null
  loading: boolean
  places: OpenNowPlace[]
}

export const OpenNowResults = ({ error, loading, places }: Props) => {
  if (!loading && !error && places.length === 0) {
    return <section className="places-page-section">
      <div className="cg-card empty-state-card">
        <h2>Пока не хватает расписаний</h2>
        <p>Можно посмотреть общий список мест, а время работы мы покажем там, где оно уже проверено.</p>
        <a className="button button-primary" href="/places">Смотреть все места</a>
      </div>
      <DiagnosticsPanel compact payload={{ screen: 'open_now', category: 'open_now', severity: 'warning', title: 'Open now empty', summary: '0 open places', response_summary: { total_places: 0, open_count: 0 } }} />
    </section>
  }
  return (
    <section className="places-page-section">
      <PlaceList places={places} loading={loading} error={error} />
      <DiagnosticsPanel compact payload={{ screen: 'open_now', category: 'open_now', severity: error ? 'error' : 'info', title: 'Open now diagnostics', summary: `${places.length} open places`, response_summary: { open_count: places.length } }} />
    </section>
  )
}
