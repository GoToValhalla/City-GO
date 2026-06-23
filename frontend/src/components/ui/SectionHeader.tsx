import type { ReactNode } from 'react'

type SectionHeaderProps = {
  eyebrow?: string
  title: string
  description?: string
  right?: ReactNode
  className?: string
}

const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(' ')

export const SectionHeader = ({
  className,
  description,
  eyebrow,
  right,
  title,
}: SectionHeaderProps) => {
  return (
    <div className={classNames('section-header', className)}>
      <div>
        {eyebrow ? <div className="section-header__eyebrow">{eyebrow}</div> : null}
        <h2 className="section-header__title">{title}</h2>
        {description ? <p className="section-header__description">{description}</p> : null}
      </div>
      {right ? <div className="section-header__right">{right}</div> : null}
    </div>
  )
}
