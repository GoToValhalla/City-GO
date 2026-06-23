import type { HTMLAttributes, ReactNode } from 'react'

type CardVariant = 'default' | 'elevated' | 'interactive'

type CardProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode
  variant?: CardVariant
}

const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(' ')

export const Card = ({ children, className, variant = 'default', ...props }: CardProps) => {
  return (
    <div className={classNames('cg-card', `cg-card--${variant}`, className)} {...props}>
      {children}
    </div>
  )
}
