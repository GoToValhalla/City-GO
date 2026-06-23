import { Building2, Camera, Coffee, Landmark, MapPinned, Trees, Utensils } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useState } from 'react'
import { categoryLabel } from '../../shared/place/categoryLabels'

type PlacePhotoSize = 'thumb' | 'card' | 'hero'

type PlacePhotoProps = {
  imageUrl?: string | null
  title: string
  category?: string | null
  size?: PlacePhotoSize
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

export const PlacePhoto = ({
  category,
  className,
  imageUrl,
  size = 'card',
  title,
}: PlacePhotoProps) => {
  const [failed, setFailed] = useState(false)
  const hasImage = Boolean(imageUrl) && !failed
  const Icon = CATEGORY_ICONS[category ?? ''] ?? MapPinned
  const label = categoryLabel(category ?? '')

  return (
    <div className={classNames('cg-place-photo', `cg-place-photo--${size}`, className)}>
      {hasImage ? (
        <img
          className="cg-place-photo__image"
          src={imageUrl ?? ''}
          alt={title}
          loading={size === 'hero' ? 'eager' : 'lazy'}
          onError={() => setFailed(true)}
        />
      ) : (
        <div className="cg-place-photo__fallback" role="img" aria-label={`Нет фото: ${title}`}>
          <span className="cg-place-photo__icon">
            <Icon size={size === 'thumb' ? 18 : 24} aria-hidden="true" />
          </span>
          {size !== 'thumb' ? (
            <>
              <span className="cg-place-photo__title cg-clamp-2">{title}</span>
              <span className="cg-place-photo__category cg-clamp-1">{label}</span>
            </>
          ) : null}
        </div>
      )}
    </div>
  )
}
