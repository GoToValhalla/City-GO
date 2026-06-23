import type { Place } from '../../entities/place/model/types'
import { EmptyState, ErrorState } from '../ui'
import { PlaceCard } from './PlaceCard'

type PlaceListProps = {
  places: Place[]
  loading?: boolean
  loadingMore?: boolean
  error?: string | null
  noCity?: boolean
  activePlaceId?: number | null
  onActivePlaceChange?: (placeId: number) => void
  onRetry?: () => void
  onResetFilters?: () => void
  onSelectCity?: () => void
  className?: string
}

const INITIAL_SKELETON_COUNT = 5
const MORE_SKELETON_COUNT = 2
const VIRTUALIZATION_THRESHOLD = 50
const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(' ')

const renderSkeletons = (count: number) => (
  Array.from({ length: count }, (_, index) => (
    <article className="cg-card place-ui-card place-ui-card-skeleton" key={index} aria-label="Загрузка карточки места">
      <span className="cg-skeleton-photo place-ui-skeleton-thumb" />
      <span className="place-ui-card__content">
        <span className="cg-skeleton-line cg-skeleton-line--medium" />
        <span className="cg-skeleton-line cg-skeleton-line--title" />
        <span className="cg-skeleton-line cg-skeleton-line--long" />
        <span className="cg-skeleton-line cg-skeleton-line--short" />
      </span>
    </article>
  ))
)

export const PlaceList = ({
  activePlaceId,
  className,
  error,
  loading = false,
  loadingMore = false,
  noCity = false,
  onActivePlaceChange,
  onResetFilters,
  onRetry,
  onSelectCity,
  places,
}: PlaceListProps) => {
  if (noCity) {
    return (
      <EmptyState
        title="Город не выбран"
        description="Выберите город, чтобы увидеть места рядом и собрать маршрут."
        actionLabel="Выбрать город"
        onAction={onSelectCity}
      />
    )
  }

  if (error) {
    return (
      <ErrorState
        title="Не удалось загрузить места"
        description={error}
        retryLabel="Повторить"
        onRetry={onRetry}
      />
    )
  }

  if (loading && places.length === 0) {
    return <div className={classNames('place-ui-list', className)}>{renderSkeletons(INITIAL_SKELETON_COUNT)}</div>
  }

  if (!loading && places.length === 0) {
    return (
      <EmptyState
        title="Ничего не найдено"
        description="Попробуйте изменить запрос или сбросить фильтры."
        actionLabel="Сбросить фильтры"
        onAction={onResetFilters}
      />
    )
  }

  return (
    <div
      className={classNames(
        'place-ui-list',
        places.length > VIRTUALIZATION_THRESHOLD && 'place-ui-list--virtualized',
        className,
      )}
    >
      {places.map((place) => (
        <PlaceCard
          key={place.id}
          place={place}
          active={activePlaceId === place.id}
          onActivate={(selected) => onActivePlaceChange?.(selected.id)}
        />
      ))}
      {loadingMore ? <div className="place-ui-list__more">{renderSkeletons(MORE_SKELETON_COUNT)}</div> : null}
    </div>
  )
}