import { Star } from 'lucide-react'

type RatingBadgeProps = {
  rating: number | null | undefined
  className?: string
}

const formatter = new Intl.NumberFormat('ru-RU', {
  maximumFractionDigits: 1,
})

const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(' ')

export const RatingBadge = ({ rating, className }: RatingBadgeProps) => {
  if (rating == null) return null

  return (
    <span className={classNames('cg-rating-badge', className)} aria-label={`Рейтинг ${formatter.format(rating)}`}>
      <Star size={13} fill="currentColor" aria-hidden="true" />
      {formatter.format(rating)}
    </span>
  )
}
