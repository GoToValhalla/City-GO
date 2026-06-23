import { Building2, Camera, Coffee, Landmark, MapPinned, Trees, Utensils } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { Place } from '../../entities/place/model/types'
import { placeStatus } from './placeViewModel'

type PlaceMapPinProps = {
  place: Place
  active?: boolean
  onClick?: (place: Place) => void
  className?: string
}

const CATEGORY_ICONS: Record<string, LucideIcon> = {
  attraction: Landmark,
  bar: Camera,
  cafe: Coffee,
  coffee: Coffee,
  culture: Landmark,
  food: Utensils,
  hotel: Building2,
  museum: Landmark,
  park: Trees,
  walk: MapPinned,
}

const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(' ')

export const PlaceMapPin = ({ active = false, className, onClick, place }: PlaceMapPinProps) => {
  const Icon = CATEGORY_ICONS[place.category] ?? MapPinned
  const closed = placeStatus(place) === 'closed'

  return (
    <button
      className={classNames('place-map-pin', active && 'is-active', closed && 'is-closed', className)}
      type="button"
      onClick={() => onClick?.(place)}
      aria-label={`Выбрать место: ${place.title}`}
    >
      <Icon size={17} aria-hidden="true" />
    </button>
  )
}
