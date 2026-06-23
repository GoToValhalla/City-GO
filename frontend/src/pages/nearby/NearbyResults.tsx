import { PlaceList } from '../../components/places'
import type { NearbyPlace } from '../../api/nearby/nearby.api'

type Props = {
  error: string | null
  loading: boolean
  places: NearbyPlace[]
}

export const NearbyResults = ({ error, loading, places }: Props) => {
  return (
    <section className="places-page-section">
      <PlaceList places={places} loading={loading} error={error} />
    </section>
  )
}
