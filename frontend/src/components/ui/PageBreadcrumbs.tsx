import { Link } from 'react-router-dom'
import type { ReactNode } from 'react'

type BreadcrumbItem = {
  label: string
  to?: string
}

type PageBreadcrumbsProps = {
  items: BreadcrumbItem[]
  right?: ReactNode
}

export const PageBreadcrumbs = ({ items, right }: PageBreadcrumbsProps) => {
  return (
    <header
      className="app-header places-header"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '16px',
        flexWrap: 'wrap',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
        {items.map((item, index) => {
          const isLast = index === items.length - 1

          return (
            <div
              key={`${item.label}-${index}`}
              style={{ display: 'flex', alignItems: 'center', gap: '12px' }}
            >
              {item.to && !isLast ? (
                <Link
                  to={item.to}
                  style={{ color: '#2563eb', textDecoration: 'none', fontWeight: 600 }}
                >
                  {item.label}
                </Link>
              ) : (
                <span style={{ fontWeight: 700, color: '#0f172a' }}>{item.label}</span>
              )}

              {!isLast ? <span style={{ color: '#94a3b8' }}>/</span> : null}
            </div>
          )
        })}
      </div>

      {right ? <div>{right}</div> : null}
    </header>
  )
}
