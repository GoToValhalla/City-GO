import { PlaceList } from '../../components/places'
import type { NearbyPlace } from '../../api/nearby/nearby.api'
import { DiagnosticsPanel } from '../../shared/debug/DiagnosticsPanel'

const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(' ')

type Props = {
  error: string | null
  loading: boolean
  places: NearbyPlace[]
  activePlaceId?: number | null
  onActivePlaceChange?: (id: number) => void
  onRetry?: () => void
}

export const NearbyResults = ({ activePlaceId, error, loading, onActivePlaceChange, onRetry, places }: Props) => {
  const blockingError = places.length === 0 ? error : null
  const transientError = places.length > 0 ? error : null
  if (!loading && !error && places.length === 0) {
    return <section className="places-page-section">
      <div className="cg-card empty-state-card">
        <h2>Рядом пока ничего не найдено</h2>
        <p>Попробуйте центр города или увеличьте радиус поиска.</p>
        <button type="button" onClick={onRetry}>Обновить поиск</button>
      </div>
      <DiagnosticsPanel compact payload={{ screen: 'nearby', category: 'nearby', severity: 'warning', title: 'Nearby empty', summary: '0 nearby places', response_summary: { candidate_count: 0, filtered_count: 0 } }} />
    </section>
  }

  return (
    <section className="places-page-section">
      {transientError ? (
        <div className={classNames('nearby-inline-error', loading && 'is-loading')} role="status">
          <span>{transientError}</span>
          <button type="button" onClick={onRetry}>Повторить</button>
        </div>
      ) : null}
      <PlaceList places={places} loading={loading} error={blockingError}
        activePlaceId={activePlaceId} onActivePlaceChange={onActivePlaceChange} onRetry={onRetry} />
      <DiagnosticsPanel compact payload={{ screen: 'nearby', category: 'nearby', severity: error ? 'error' : 'info', title: 'Nearby diagnostics', summary: `${places.length} nearby places`, response_summary: { nearby_count: places.length } }} />
    </section>
  )
}
