import type { CSSProperties, ReactNode } from 'react'

type SurfaceCardProps = {
  children: ReactNode
  style?: CSSProperties
}

const baseStyle: CSSProperties = {
  background: 'rgba(255, 255, 255, 0.88)',
  borderRadius: '8px',
  border: '1px solid rgba(148, 163, 184, 0.18)',
  boxShadow: '0 14px 30px rgba(15, 23, 42, 0.05)',
  backdropFilter: 'blur(12px)',
}

export const SurfaceCard = ({ children, style }: SurfaceCardProps) => {
  return <div style={{ ...baseStyle, ...style }}>{children}</div>
}
