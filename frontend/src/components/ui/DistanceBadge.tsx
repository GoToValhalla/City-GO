import { Navigation } from 'lucide-react'

type DistanceBadgeProps = {
  distance: string | null | undefined
  className?: string
}

const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(' ')

export const DistanceBadge = ({ distance, className }: DistanceBadgeProps) => {
  if (!distance) return null

  return (
    <span className={classNames('cg-distance-badge', className)}>
      <Navigation size={13} aria-hidden="true" />
      {distance}
    </span>
  )
}
