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
    <nav className="page-breadcrumbs" aria-label="Навигация по странице">
      <div className="page-breadcrumbs__items">
        {items.map((item, index) => {
          const isLast = index === items.length - 1

          return (
            <span className="page-breadcrumbs__item" key={`${item.label}-${index}`}>
              {item.to && !isLast ? (
                <Link to={item.to}>{item.label}</Link>
              ) : (
                <span>{item.label}</span>
              )}
              {!isLast ? <span className="page-breadcrumbs__separator">/</span> : null}
            </span>
          )
        })}
      </div>
      {right ? <div>{right}</div> : null}
    </nav>
  )
}
