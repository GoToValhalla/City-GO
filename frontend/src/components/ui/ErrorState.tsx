import { AlertTriangle } from 'lucide-react'
import type { ReactNode } from 'react'
import { Button } from './Button'

type ErrorStateProps = {
  title?: string
  description?: string
  icon?: ReactNode
  retryLabel?: string
  onRetry?: () => void
  className?: string
}

const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(' ')

export const ErrorState = ({
  className,
  description = 'Не удалось загрузить данные. Попробуйте ещё раз.',
  icon,
  onRetry,
  retryLabel = 'Повторить',
  title = 'Что-то пошло не так',
}: ErrorStateProps) => {
  return (
    <section className={classNames('cg-state', 'cg-state--error', className)}>
      <div className="cg-state__icon" aria-hidden="true">
        {icon ?? <AlertTriangle size={22} />}
      </div>
      <strong className="cg-state__title">{title}</strong>
      <p className="cg-state__description">{description}</p>
      {onRetry ? (
        <div className="cg-state__action">
          <Button variant="danger" size="sm" onClick={onRetry}>{retryLabel}</Button>
        </div>
      ) : null}
    </section>
  )
}
