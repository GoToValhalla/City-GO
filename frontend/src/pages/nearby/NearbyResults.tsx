import { PlaceList } from '../../components/places'
import type { NearbyPlace } from '../../api/nearby/nearby.api'

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
    </section>
  )
}
