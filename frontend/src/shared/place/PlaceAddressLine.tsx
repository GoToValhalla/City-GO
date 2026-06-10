import { MapPin } from 'lucide-react'
import { MAP_LINK_LABEL, placeAddressView, type AddressPlace } from './placeAddress'

type Props = {
  place: AddressPlace
  className?: string
}

export const PlaceAddressLine = ({ place, className = 'place-meta' }: Props) => {
  const view = placeAddressView(place)
  return (
    <div className={view.unclear ? `${className} place-address-unclear` : className}>
      <MapPin size={16} />
      <span>{view.label}</span>
      {view.unclear && view.mapUrl ? (
        <a className="place-map-link" href={view.mapUrl} target="_blank" rel="noopener noreferrer">
          {MAP_LINK_LABEL}
        </a>
      ) : null}
    </div>
  )
}
