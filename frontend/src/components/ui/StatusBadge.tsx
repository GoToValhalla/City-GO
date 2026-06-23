export type PlaceStatus = 'open' | 'closed' | 'unknown' | 'soon'

type StatusBadgeProps = {
  status: PlaceStatus
  className?: string
}

const STATUS_LABELS: Record<PlaceStatus, string> = {
  open: 'Открыто',
  closed: 'Закрыто',
  unknown: 'Уточнить',
  soon: 'Скоро закроется',
}

const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(' ')

export const StatusBadge = ({ status, className }: StatusBadgeProps) => {
  return (
    <span className={classNames('cg-status-badge', `cg-status-badge--${status}`, className)}>
      {STATUS_LABELS[status]}
    </span>
  )
}
