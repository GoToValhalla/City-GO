import { categoryLabel } from '../../shared/place/categoryLabels'

type CategoryBadgeProps = {
  category: string | null | undefined
  className?: string
}

const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(' ')

export const CategoryBadge = ({ category, className }: CategoryBadgeProps) => {
  return (
    <span className={classNames('cg-category-badge', className)}>
      {categoryLabel(category ?? '')}
    </span>
  )
}
