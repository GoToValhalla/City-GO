import { PlaceList } from '../../components/places'
import type { OpenNowPlace } from '../../api/open-now/openNow.api'

type Props = {
  error: string | null
  loading: boolean
  places: OpenNowPlace[]
}

export const OpenNowResults = ({ error, loading, places }: Props) => {
  return (
    <section className="places-page-section">
      <PlaceList places={places} loading={loading} error={error} />
    </section>
  )
}
