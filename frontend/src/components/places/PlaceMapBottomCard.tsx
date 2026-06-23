import { Link } from 'react-router-dom'
import type { Place } from '../../entities/place/model/types'
import { CategoryBadge, PlacePhoto, StatusBadge } from '../ui'
import { placeImageUrl, placeStatus, placeTitle } from './placeViewModel'

type PlaceMapBottomCardProps = {
  place: Place
  className?: string
}

const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(' ')

export const PlaceMapBottomCard = ({ className, place }: PlaceMapBottomCardProps) => {
  const status = placeStatus(place)
  const title = placeTitle(place)

  return (
    <Link className={classNames('place-map-bottom-card', className)} to={`/places/${place.slug}`}>
      <PlacePhoto
        imageUrl={placeImageUrl(place)}
        title={title}
        category={place.category}
        size="thumb"
        closed={status === 'closed'}
      />
      <div className="place-map-bottom-card__copy">
        <strong className="place-map-bottom-card__title cg-clamp-2">{title}</strong>
        <div className="place-ui-card__meta">
          <CategoryBadge category={place.category} />
          <StatusBadge status={status} />
        </div>
      </div>
    </Link>
  )
}
