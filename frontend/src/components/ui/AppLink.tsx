import { Link } from 'react-router-dom'
import type { ReactNode } from 'react'

type AppLinkProps = {
  to: string
  children: ReactNode
  variant?: 'primary' | 'secondary' | 'ghost'
}

const styles = {
  base: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    textDecoration: 'none',
    fontWeight: 600,
    transition: 'all 0.18s ease',
    cursor: 'pointer',
  },
  primary: {
    minHeight: '44px',
    padding: '0 16px',
    borderRadius: '14px',
    border: '1px solid rgba(255, 255, 255, 0.14)',
    background: 'rgba(255, 255, 255, 0.08)',
    color: '#ffffff',
    fontSize: '14px',
    backdropFilter: 'blur(10px)',
  },
  secondary: {
    color: '#2563eb',
    fontSize: '14px',
  },
  ghost: {
    minHeight: '40px',
    padding: '0 14px',
    borderRadius: '999px',
    background: 'rgba(255, 255, 255, 0.78)',
    border: '1px solid rgba(148, 163, 184, 0.18)',
    color: '#334155',
    fontSize: '14px',
  },
} as const

export const AppLink = ({ to, children, variant = 'secondary' }: AppLinkProps) => {
  const style = {
    ...styles.base,
    ...styles[variant],
  }

  return (
    <Link to={to} style={style}>
      {children}
    </Link>
  )
}
