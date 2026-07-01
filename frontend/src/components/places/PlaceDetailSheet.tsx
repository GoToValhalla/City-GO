import { ArrowLeft, ChevronLeft, ChevronRight, Clock3, Globe2, MapPin, Phone, Sparkles } from 'lucide-react'
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

type FactRowProps = {
  icon: ReactNode
  label: string
  children: ReactNode
}

const DESCRIPTION_LIMIT = 320
const TEMPLATE_DETAILS = new Set([
  'еда и отдых',
  'зал, меню и возможность сделать паузу',
  'кофе, перекус или спокойная остановка в маршруте',
  'культура и история',
  'экспозиции, архитектурные детали или исторический контекст',
  'первое знакомство с городом и неспешная прогулка',
  'прогулка на свежем воздухе',
  'открытое пространство и точки для остановки',
  'прогулка, фото и спокойный маршрут',
])

const meaningfulDetail = (value: string | null): string | null => {
  if (!value) return null
  const normalized = value.trim().toLowerCase().replace(/[.!]+$/, '')
  return TEMPLATE_DETAILS.has(normalized) ? null : value.trim()
}

const FactRow = ({ children, icon, label }: FactRowProps) => (
  <div className="place-detail-fact">
    <span className="place-detail-fact__icon" aria-hidden="true">{icon}</span>
    <div><span className="place-detail-fact__label">{label}</span><div className="place-detail-fact__value">{children}</div></div>
  </div>
)

export const PlaceDetailSheet = ({ onAddToRoute, place }: PlaceDetailSheetProps) => {
  const [expanded, setExpanded] = useState(false)
  const [photoIndex, setPhotoIndex] = useState(0)
  const title = placeTitle(place)
  const status = placeStatus(place)
  const description = placeDescription(place)
  const gallery = placeGallery(place)
  const fallbackImageUrl = placeImageUrl(place)
  const safePhotoIndex = gallery.length ? Math.min(photoIndex, gallery.length - 1) : 0
  const imageUrl = gallery[safePhotoIndex] ?? fallbackImageUrl
  const address = placeAddressLabel(place)
  const hours = placeHoursLabel(place)
  const atmosphere = meaningfulDetail(listText(place.atmosphere))
  const inside = meaningfulDetail(listText(place.inside))
  const bestFor = meaningfulDetail(listText(place.best_for))
  const featureLabels = [...placeTagLabels(place), ...placeFeatureLabels(place)]
    .filter((value, index, list) => Boolean(value) && list.indexOf(value) === index)
    .slice(0, 6)
  const descriptionPending = !description || description.length < 80
  const shouldCollapseDescription = Boolean(description && description.length > DESCRIPTION_LIMIT)
  const visibleDescription = description && shouldCollapseDescription && !expanded
    ? `${description.slice(0, DESCRIPTION_LIMIT).trim()}...`
    : description
  const showCarousel = gallery.length > 1
  const showPreviousPhoto = () => setPhotoIndex((value) => (value <= 0 ? gallery.length - 1 : value - 1))
  const showNextPhoto = () => setPhotoIndex((value) => (value >= gallery.length - 1 ? 0 : value + 1))
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
    <main className="place-detail-sheet place-detail-sheet--refined">
      <div className="place-detail-sheet__media">
        {imageUrl ? (
          <a href={imageUrl} target="_blank" rel="noopener noreferrer" aria-label={`Открыть фото ${safePhotoIndex + 1} из ${Math.max(gallery.length, 1)}: ${title}`}>
            {hero}
          </a>
        ) : hero}
        {showCarousel ? (
          <div className="place-photo-carousel" aria-label={`Фотографии места: ${title}`}>
            <button className="place-photo-carousel__nav" type="button" onClick={showPreviousPhoto} aria-label="Предыдущее фото"><ChevronLeft size={18} /></button>
            <div className="place-photo-carousel__dots" role="tablist" aria-label="Выбор фото">
              {gallery.map((url, index) => (
                <button
                  key={`${url}-${index}`}
                  className={index === safePhotoIndex ? 'place-photo-carousel__dot place-photo-carousel__dot--active' : 'place-photo-carousel__dot'}
                  type="button"
                  onClick={() => setPhotoIndex(index)}
                  aria-label={`Показать фото ${index + 1} из ${gallery.length}`}
                  aria-selected={index === safePhotoIndex}
                >
                  {index + 1}
                </button>
              ))}
            </div>
            <button className="place-photo-carousel__nav" type="button" onClick={showNextPhoto} aria-label="Следующее фото"><ChevronRight size={18} /></button>
          </div>
        ) : null}
      </div>

      <section className="place-detail-sheet__panel">
        <Link className="place-detail-sheet__back" to="/places"><ArrowLeft size={17} /> Места</Link>

        <div className="place-detail-sheet__badges">
          <CategoryBadge category={place.category} />
          <StatusBadge status={status} />
          <RatingBadge rating={placeRating(place)} reviewCount={placeReviewCount(place)} />
        </div>

        <h1 className="place-detail-sheet__title">{title}</h1>

        <div className="place-detail-sheet__description">
          {visibleDescription ? <p>{visibleDescription}</p> : null}
          {descriptionPending ? <p className="place-detail-sheet__pending">Подробное описание дополняется. Ниже показаны только подтверждённые данные карточки.</p> : null}
          {shouldCollapseDescription ? (
            <button className="place-detail-sheet__read-more" type="button" onClick={() => setExpanded((value) => !value)}>
              {expanded ? 'Свернуть' : 'Читать дальше'}
            </button>
          ) : null}
        </div>

        {featureLabels.length ? <div className="place-detail-features">{featureLabels.map((feature) => <span key={feature}>{feature}</span>)}</div> : null}

        <section className="place-detail-facts" aria-label="Основная информация">
          {address ? <FactRow icon={<MapPin size={18} />} label="Адрес">{address}</FactRow> : null}
          {hours ? <FactRow icon={<Clock3 size={18} />} label="Часы работы">{hours}</FactRow> : null}
          {place.phone ? <FactRow icon={<Phone size={18} />} label="Телефон"><a href={`tel:${place.phone}`}>{place.phone}</a></FactRow> : null}
          {place.website ? <FactRow icon={<Globe2 size={18} />} label="Сайт"><a href={place.website} target="_blank" rel="noopener noreferrer">Открыть сайт</a></FactRow> : null}
        </section>

        {atmosphere || inside || bestFor ? <section className="place-detail-editorial" aria-label="Дополнительная информация">
          <h2><Sparkles size={18} /> Об этом месте</h2>
          {atmosphere ? <p><strong>Атмосфера:</strong> {atmosphere}</p> : null}
          {inside ? <p><strong>Особенности:</strong> {inside}</p> : null}
          {bestFor ? <p><strong>Подойдёт для:</strong> {bestFor}</p> : null}
        </section> : null}

        <footer className="place-detail-sheet__footer">
          <Link className="cg-button cg-button--primary cg-button--lg" to="/routes/generate">Построить маршрут</Link>
          {onAddToRoute ? <Button variant="secondary" size="lg" onClick={onAddToRoute}>Добавить в маршрут</Button> : null}
          {place.phone ? <a className="cg-button cg-button--ghost cg-button--lg" href={`tel:${place.phone}`}>Позвонить</a> : null}
          {place.website ? <a className="cg-button cg-button--ghost cg-button--lg" href={place.website} target="_blank" rel="noopener noreferrer">Сайт</a> : null}
        </footer>
      </section>
    </main>
  )
}
