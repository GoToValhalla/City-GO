import { Clock, ExternalLink, Timer, WalletCards } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { Place } from '../../entities/place/model/types'
import {
  categoryLabel,
  priceLabel,
  timeLabel,
} from '../../shared/demo/categoryLabels'
import {
  cleanPlaceDescription,
  photoStateLabel,
  placeFeatureLabels,
  verifiedImageUrl,
} from '../../shared/demo/placePresentation'
import { PlaceAddressLine } from '../../shared/place/PlaceAddressLine'

type PlaceCardProps = {
  place: Place
}

export const PlaceCard = ({ place }: PlaceCardProps) => {
  const imageUrl = verifiedImageUrl(place)
  const features = placeFeatureLabels(place).slice(0, 3)

  return (
    <article className="place-card">
      <Link className="place-card-media" to={`/places/${place.slug}`}>
        {imageUrl ? <img src={imageUrl} alt={place.title} loading="lazy" /> : (
          <div className="place-card-fallback">
            <span>{categoryLabel(place.category)}</span>
            <strong>{place.title}</strong>
          </div>
        )}
        <span className="place-image-badge">{photoStateLabel(place)}</span>
      </Link>

      <div className="place-card-body">
        <span className="place-chip">{categoryLabel(place.category)}</span>

        <h3 className="place-card-title">
          <Link className="place-card-link" to={`/places/${place.slug}`}>
            {place.title}
          </Link>
        </h3>

        <PlaceAddressLine place={place} />

        <p className="place-description">
          {cleanPlaceDescription(place)}
        </p>

        {features.length > 0 ? <div className="place-tag-row">
          {features.map((item) => <span key={item}>{item}</span>)}
        </div> : null}

        <div className="place-facts">
          <span><Clock size={14} /> {timeLabel(place.open_time, place.close_time)}</span>
          <span><Timer size={14} /> {place.visit_minutes ? `${place.visit_minutes} мин` : 'уточнить'}</span>
          <span><WalletCards size={14} /> {priceLabel(place.price_level)}</span>
        </div>

        <Link className="place-card-link-secondary" to={`/places/${place.slug}`}>
          Подробнее <ExternalLink size={14} />
        </Link>
      </div>
    </article>
  )
}
