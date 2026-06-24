import { Link } from 'react-router-dom'
import { useState } from 'react'
import type { ReactNode } from 'react'
import type { PlaceDetail } from '../../entities/place/model/types'
import { Button, CategoryBadge, PlacePhoto, RatingBadge, StatusBadge } from '../ui'
import {
  listText,
  placeAddressLabel,
  placeDescription,
  placeFeatureLabels,
  placeGallery,
  placeHoursLabel,
  placeImageUrl,
  placeRating,
  placeReviewCount,
  placeStatus,
  placeTagLabels,
  placeTitle,
} from './placeViewModel'

type PlaceDetailSheetProps = {
  place: PlaceDetail
  onAddToRoute?: () => void
}

type DetailSectionProps = {
  title: string
  children: ReactNode
}

const DESCRIPTION_LIMIT = 260

const DetailSection = ({ children, title }: DetailSectionProps) => {
  return (
    <section className="place-detail-section">
      <strong className="place-detail-section__title">{title}</strong>
      <div className="place-detail-section__body">{children}</div>
    </section>
  )
}

export const PlaceDetailSheet = ({ onAddToRoute, place }: PlaceDetailSheetProps) => {
  const [expanded, setExpanded] = useState(false)
  const title = placeTitle(place)
  const status = placeStatus(place)
  const description = placeDescription(place)
  const gallery = placeGallery(place)
  const imageUrl = gallery[0] ?? placeImageUrl(place)
  const address = placeAddressLabel(place)
  const hours = placeHoursLabel(place)
  const atmosphere = listText(place.atmosphere) ?? placeTagLabels(place).join(', ')
  const inside = listText(place.inside)
  const bestFor = listText(place.best_for) ?? placeFeatureLabels(place).join(', ')
  const shouldCollapseDescription = Boolean(description && description.length > DESCRIPTION_LIMIT)
  const visibleDescription = description && shouldCollapseDescription && !expanded
    ? `${description.slice(0, DESCRIPTION_LIMIT).trim()}...`
    : description
  const hero = (
    <PlacePhoto
      imageUrl={imageUrl}
      title={title}
      category={place.category}
      size="hero"
      fallbackLabel="Фото скоро появятся"
      closed={status === 'closed'}
    />
  )

  return (
    <main className="place-detail-sheet">
      <div className="place-detail-sheet__media">
        {imageUrl ? (
          <a href={imageUrl} target="_blank" rel="noopener noreferrer" aria-label={`Открыть фото: ${title}`}>
            {hero}
          </a>
        ) : hero}
      </div>

      <section className="place-detail-sheet__panel">
        <Link className="place-detail-sheet__back" to="/places">Все места</Link>

        <div className="place-detail-sheet__badges">
          <CategoryBadge category={place.category} />
          <StatusBadge status={status} />
          <RatingBadge rating={placeRating(place)} reviewCount={placeReviewCount(place)} />
        </div>

        <h1 className="place-detail-sheet__title">{title}</h1>

        {visibleDescription ? (
          <div className="place-detail-sheet__description">
            <p className={expanded ? undefined : 'cg-clamp-3'}>{visibleDescription}</p>
            {shouldCollapseDescription ? (
              <button className="place-detail-sheet__read-more" type="button" onClick={() => setExpanded((value) => !value)}>
                {expanded ? 'Свернуть' : 'Читать дальше'}
              </button>
            ) : null}
          </div>
        ) : null}

        {atmosphere ? <DetailSection title="Атмосфера">{atmosphere}</DetailSection> : null}
        {inside ? <DetailSection title="Что внутри">{inside}</DetailSection> : null}
        {bestFor ? <DetailSection title="Кому подойдёт">{bestFor}</DetailSection> : null}
        {address ? <DetailSection title="Адрес">{address}</DetailSection> : null}
        {hours ? <DetailSection title="Часы работы">{hours}</DetailSection> : null}
        {place.phone || place.website ? (
          <DetailSection title="Контакты">
            {place.phone ? <div>{place.phone}</div> : null}
            {place.website ? <a href={place.website} target="_blank" rel="noopener noreferrer">Открыть сайт</a> : null}
          </DetailSection>
        ) : null}

        <footer className="place-detail-sheet__footer">
          <Link className="cg-button cg-button--primary cg-button--lg" to="/routes/generate">Построить маршрут</Link>
          <Button variant="secondary" size="lg" onClick={onAddToRoute} disabled={!onAddToRoute}>Добавить в маршрут</Button>
          {place.phone ? <a className="cg-button cg-button--ghost cg-button--lg" href={`tel:${place.phone}`}>Позвонить</a> : null}
          {place.website ? <a className="cg-button cg-button--ghost cg-button--lg" href={place.website} target="_blank" rel="noopener noreferrer">Сайт</a> : null}
        </footer>
      </section>
    </main>
  )
}