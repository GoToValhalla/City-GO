import { placeCategoryLabel } from './placeViewModel'

export type FilterChipOption = {
  value: string
  label?: string
  count?: number
}

type FilterChipsProps = {
  options: FilterChipOption[]
  value: string
  onChange: (value: string) => void
  className?: string
}

const ALL_VALUE = 'all'
const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(' ')

export const FilterChips = ({ className, onChange, options, value }: FilterChipsProps) => {
  const allOptions: FilterChipOption[] = [{ value: ALL_VALUE, label: 'Все' }, ...options]

  return (
    <div className={classNames('filter-chips', className)} role="list" aria-label="Фильтр категорий">
      {allOptions.map((option) => {
        const isActive = option.value === value
        const disabled = option.value !== ALL_VALUE && option.count === 0
        const label = option.label ?? placeCategoryLabel(option.value)

        return (
          <button
            key={option.value}
            className={classNames('filter-chip', isActive && 'is-active')}
            type="button"
            disabled={disabled}
            onClick={() => onChange(option.value)}
            aria-pressed={isActive}
          >
            {label}
            {typeof option.count === 'number' ? <span>{option.count}</span> : null}
          </button>
        )
      })}
    </div>
  )
}

export { ALL_VALUE }
