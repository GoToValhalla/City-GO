import type { CSSProperties, ReactNode } from 'react'

type BadgeVariant = 'neutral' | 'brand' | 'success'

type BadgeProps = {
  children: ReactNode
  variant?: BadgeVariant
  uppercase?: boolean
}

const baseStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '7px 11px',
  borderRadius: '999px',
  fontSize: '12px',
  fontWeight: 800,
  letterSpacing: '0.06em',
}

const variantStyles: Record<BadgeVariant, CSSProperties> = {
  neutral: {
    background: '#f1f5f9',
    color: '#334155',
  },
  brand: {
    background: '#eff6ff',
    color: '#2563eb',
  },
  success: {
    background: '#dcfce7',
    color: '#166534',
  },
}

export const Badge = ({ children, variant = 'neutral', uppercase = false }: BadgeProps) => {
  return (
    <span
      style={{
        ...baseStyle,
        ...variantStyles[variant],
        textTransform: uppercase ? 'uppercase' : 'none',
      }}
    >
      {children}
    </span>
  )
}
