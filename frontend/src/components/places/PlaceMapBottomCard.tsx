import { ChevronRight, MapPin, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { Place } from '../../entities/place/model/types'
import { CategoryBadge, PlacePhoto, RatingBadge, StatusBadge } from '../ui'
import {
  placeAddressLabel,
  placeDescription,
  placeImageUrl,
  placeRating,
  placeReviewCount,
  placeStatus,
  placeTitle,
} from './placeViewModel'

type PlaceMapBottomCardProps = {
  place: Place
  className?: string
  onClose?: () => void
}

const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(' ')

export const PlaceMapBottomCard = ({ className, onClose, place }: PlaceMapBottomCardProps) => {
  const status = placeStatus(place)
  const title = placeTitle(place)
  const description = placeDescription(place)
  const address = placeAddressLabel(place)

  return (
    <article className={classNames('place-map-bottom-card', className)} aria-label={`Выбрано место: ${title}`}>
      <Link className="place-map-bottom-card__main" to={`/places/${place.slug}`}>
        <PlacePhoto
          imageUrl={placeImageUrl(place)}
          title={title}
          category={place.category}
          size="thumb"
          closed={status === 'closed'}
        />
        <div className="place-map-bottom-card__copy">
          <div className="place-map-bottom-card__badges">
            <CategoryBadge category={place.category} />
            <StatusBadge status={status} />
            <RatingBadge rating={placeRating(place)} reviewCount={placeReviewCount(place)} />
          </div>
          <strong className="place-map-bottom-card__title cg-clamp-2">{title}</strong>
          {description ? <p className="place-map-bottom-card__description cg-clamp-2">{description}</p> : null}
          {address ? <span className="place-map-bottom-card__address cg-clamp-1"><MapPin size={13} />{address}</span> : null}
          <span className="place-map-bottom-card__open">Подробнее <ChevronRight size={15} /></span>
        </div>
      </Link>
      {onClose ? <button type="button" className="place-map-bottom-card__close" onClick={onClose} aria-label="Закрыть карточку места"><X size={18} /></button> : null}
    </article>
  )
}