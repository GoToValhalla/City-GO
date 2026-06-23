import { Star } from 'lucide-react'

type RatingBadgeProps = {
  rating: number | null | undefined
  reviewCount?: number | null
  className?: string
}

const formatter = new Intl.NumberFormat('ru-RU', {
  maximumFractionDigits: 1,
})

const countFormatter = new Intl.NumberFormat('ru-RU')

const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(' ')

export const RatingBadge = ({ rating, reviewCount, className }: RatingBadgeProps) => {
  if (rating == null || !Number.isFinite(rating)) return null

  const hasReviewCount = typeof reviewCount === 'number' && Number.isFinite(reviewCount) && reviewCount > 0
  const label = hasReviewCount
    ? `Рейтинг ${formatter.format(rating)}, отзывов ${countFormatter.format(reviewCount)}`
    : `Рейтинг ${formatter.format(rating)}`

  return (
    <span className={classNames('cg-rating-badge', className)} aria-label={label}>
      <Star size={13} fill="currentColor" aria-hidden="true" />
      {formatter.format(rating)}
      {hasReviewCount ? <span>· {countFormatter.format(reviewCount)} отзывов</span> : null}
    </span>
  )
}
