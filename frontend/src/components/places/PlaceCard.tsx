import { ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { Place } from '../../entities/place/model/types'
import { UNCLEAR_ADDRESS_LABEL } from '../../shared/place/placeAddress'
import { photoStateLabel } from '../../shared/demo/placePresentation'
import { CategoryBadge, DistanceBadge, PlacePhoto, RatingBadge, StatusBadge } from '../ui'
import {
  placeAddressLabel,
  placeDescription,
  placeDistanceLabel,
  placeImageUrl,
  placeRating,
  placeReviewCount,
  placeStatus,
  placeTitle,
} from './placeViewModel'

type PlaceCardProps = {
  place: Place
  active?: boolean
  className?: string
  onActivate?: (place: Place) => void
}

const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(' ')

export const PlaceCard = ({ active = false, className, onActivate, place }: PlaceCardProps) => {
  const status = placeStatus(place)
  const title = placeTitle(place)
  const description = placeDescription(place)
  const distance = placeDistanceLabel(place)
  const address = placeAddressLabel(place) ?? UNCLEAR_ADDRESS_LABEL
  const activate = () => onActivate?.(place)

  return (
    <Link
      className={classNames(
        'cg-card cg-card--interactive place-ui-card',
        status === 'closed' && 'place-ui-card--closed',
        active && 'is-active',
        className,
      )}
      to={`/places/${place.slug}`}
      aria-label={`Открыть место: ${title}`}
      onFocus={activate}
      onMouseEnter={activate}
    >
      <div className="place-ui-card__media">
        <PlacePhoto
          className="place-ui-card__photo"
          imageUrl={placeImageUrl(place)}
          title={title}
          category={place.category}
          size="thumb"
          closed={status === 'closed'}
        />
        <span className="place-ui-card__photo-state">{photoStateLabel(place)}</span>
      </div>

      <div className="place-ui-card__content">
        <div className="place-ui-card__top">
          <CategoryBadge category={place.category} />
          <StatusBadge status={status} />
          <RatingBadge rating={placeRating(place)} reviewCount={placeReviewCount(place)} />
          <DistanceBadge distance={distance} />
        </div>

        <h3 className="place-ui-card__title cg-clamp-1">{title}</h3>

        {description ? (
          <p className="place-ui-card__description cg-clamp-2">{description}</p>
        ) : null}

        <p className="place-ui-card__address cg-clamp-1">{address}</p>

        <div className="place-ui-card__actions" aria-hidden="true">
          <span className="cg-text-caption">Подробнее</span>
          <ChevronRight size={15} />
        </div>
      </div>
    </Link>
  )
}
