import { X } from 'lucide-react'
import { Button } from '../ui/Button'
import { FilterChips, type FilterChipOption } from './FilterChips'

type FilterSheetDraft = {
  category: string
  onlyOpen: boolean
  radiusKm?: number | null
  minRating?: number | null
}

type FilterSheetProps = {
  open: boolean
  value: FilterSheetDraft
  categories: FilterChipOption[]
  supportsRadius?: boolean
  supportsRating?: boolean
  onChange: (value: FilterSheetDraft) => void
  onApply: () => void
  onReset: () => void
  onClose: () => void
}

const RADIUS_OPTIONS = [1, 3, 5]
const RATING_OPTIONS = [4, 4.5]

export const FilterSheet = ({
  categories,
  onApply,
  onChange,
  onClose,
  onReset,
  open,
  supportsRadius = false,
  supportsRating = false,
  value,
}: FilterSheetProps) => {
  return (
    <aside className="filter-sheet" hidden={!open} aria-label="Фильтры мест">
      <div className="filter-sheet__head">
        <h2 className="filter-sheet__title">Фильтры</h2>
        <button className="filter-sheet__close" type="button" onClick={onClose} aria-label="Закрыть фильтры">
          <X size={20} aria-hidden="true" />
        </button>
      </div>

      <section className="filter-sheet__section">
        <span className="filter-sheet__label">Категории</span>
        <FilterChips
          options={categories}
          value={value.category}
          onChange={(category) => onChange({ ...value, category })}
        />
      </section>

      <section className="filter-sheet__section">
        <label className="filter-sheet__row filter-sheet__toggle">
          <span>Только открытые</span>
          <input
            type="checkbox"
            checked={value.onlyOpen}
            onChange={(event) => onChange({ ...value, onlyOpen: event.target.checked })}
          />
        </label>
      </section>

      {supportsRadius ? (
        <section className="filter-sheet__section">
          <span className="filter-sheet__label">Радиус</span>
          <div className="filter-sheet__grid">
            {RADIUS_OPTIONS.map((radiusKm) => (
              <button
                key={radiusKm}
                className={value.radiusKm === radiusKm ? 'filter-chip is-active' : 'filter-chip'}
                type="button"
                onClick={() => onChange({ ...value, radiusKm })}
              >
                {radiusKm} км
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {supportsRating ? (
        <section className="filter-sheet__section">
          <span className="filter-sheet__label">Рейтинг</span>
          <div className="filter-sheet__grid">
            {RATING_OPTIONS.map((minRating) => (
              <button
                key={minRating}
                className={value.minRating === minRating ? 'filter-chip is-active' : 'filter-chip'}
                type="button"
                onClick={() => onChange({ ...value, minRating })}
              >
                от {String(minRating).replace('.', ',')}
              </button>
            ))}
          </div>
        </section>
      ) : null}

      <div className="filter-sheet__actions">
        <Button variant="ghost" size="lg" onClick={onReset}>Сбросить</Button>
        <Button variant="primary" size="lg" onClick={onApply}>Применить</Button>
      </div>
    </aside>
  )
}

export type { FilterSheetDraft }
