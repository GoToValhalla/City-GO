import { PlaceList } from '../../components/places'
import type { NearbyPlace } from '../../api/nearby/nearby.api'

type Props = {
  error: string | null
  loading: boolean
  places: NearbyPlace[]
  activePlaceId?: number | null
  onActivePlaceChange?: (id: number) => void
}

export const NearbyResults = ({ activePlaceId, error, loading, onActivePlaceChange, places }: Props) => {
  return (
    <section className="places-page-section">
      <PlaceList places={places} loading={loading} error={error}
        activePlaceId={activePlaceId} onActivePlaceChange={onActivePlaceChange} />
    </section>
  )
}
