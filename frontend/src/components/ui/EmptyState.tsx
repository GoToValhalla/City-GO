import { MapPinned } from 'lucide-react'
import type { ReactNode } from 'react'
import { Button } from './Button'

type EmptyStateProps = {
  title?: string
  message?: string
  description?: string
  icon?: ReactNode
  actionLabel?: string
  onAction?: () => void
  className?: string
}

const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(' ')

export const EmptyState = ({
  actionLabel,
  className,
  description,
  icon,
  message,
  onAction,
  title,
}: EmptyStateProps) => {
  const resolvedTitle = title ?? message ?? 'Здесь пока ничего нет'

  return (
    <section className={classNames('cg-state', className)} role="status" aria-live="polite">
      <div className="cg-state__icon" aria-hidden="true">
        {icon ?? <MapPinned size={22} />}
      </div>
      <strong className="cg-state__title">{resolvedTitle}</strong>
      {description ? <p className="cg-state__description">{description}</p> : null}
      {actionLabel && onAction ? (
        <div className="cg-state__action">
          <Button variant="secondary" size="sm" onClick={onAction}>{actionLabel}</Button>
        </div>
      ) : null}
    </section>
  )
}
