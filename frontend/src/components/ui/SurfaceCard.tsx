import type { CSSProperties, ReactNode } from 'react'

type SurfaceCardProps = {
  children: ReactNode
  style?: CSSProperties
  className?: string
}

const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(' ')

export const SurfaceCard = ({ children, className, style }: SurfaceCardProps) => {
  return <div className={classNames('cg-card cg-card--default', className)} style={style}>{children}</div>
}
