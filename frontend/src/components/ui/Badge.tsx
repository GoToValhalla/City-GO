import type { ReactNode } from 'react'

type BadgeVariant = 'neutral' | 'brand' | 'success' | 'warning' | 'danger'

type BadgeProps = {
  children: ReactNode
  variant?: BadgeVariant
  uppercase?: boolean
  className?: string
}

const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(' ')

export const Badge = ({ children, className, variant = 'neutral', uppercase = false }: BadgeProps) => {
  return (
    <span className={classNames('cg-badge', `cg-badge--${variant}`, uppercase && 'cg-badge--uppercase', className)}>
      {children}
    </span>
  )
}
