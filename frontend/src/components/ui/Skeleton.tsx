type SkeletonVariant = 'card' | 'line' | 'circle'

type SkeletonProps = {
  variant?: SkeletonVariant
  className?: string
}

const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(' ')

export const Skeleton = ({ variant = 'card', className }: SkeletonProps) => {
  if (variant === 'line') {
    return <span className={classNames('cg-skeleton-line cg-skeleton-line--long', className)} aria-hidden="true" />
  }

  if (variant === 'circle') {
    return <span className={classNames('cg-skeleton-circle', className)} aria-hidden="true" />
  }

  return (
    <article className={classNames('cg-skeleton-card', className)} aria-hidden="true">
      <div className="cg-skeleton-photo" />
      <div className="cg-skeleton-line cg-skeleton-line--title" />
      <div className="cg-skeleton-line cg-skeleton-line--long" />
      <div className="cg-skeleton-line cg-skeleton-line--medium" />
      <div className="cg-skeleton-line cg-skeleton-line--short" />
    </article>
  )
}
