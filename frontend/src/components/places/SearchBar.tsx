import { Search, X } from 'lucide-react'
import { useEffect, useState } from 'react'

type SearchBarProps = {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  loading?: boolean
  error?: string | null
  className?: string
}

const DEBOUNCE_MS = 300
const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(' ')

export const SearchBar = ({
  className,
  error,
  loading = false,
  onChange,
  placeholder = 'Поиск мест в городе',
  value,
}: SearchBarProps) => {
  const [draft, setDraft] = useState(value)

  useEffect(() => {
    setDraft(value)
  }, [value])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      if (draft !== value) onChange(draft)
    }, DEBOUNCE_MS)

    return () => window.clearTimeout(timeoutId)
  }, [draft, onChange, value])

  const clearSearch = () => {
    setDraft('')
    onChange('')
  }

  return (
    <label className={classNames('place-search', className)}>
      <span className="place-search__field">
        <Search size={18} aria-hidden="true" />
        <input
          type="search"
          placeholder={placeholder}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          aria-invalid={Boolean(error) || undefined}
        />
        {loading ? <span className="place-search__loading" aria-label="Идёт поиск" /> : null}
        {!loading && draft ? (
          <button className="place-search__clear" type="button" onClick={clearSearch} aria-label="Очистить поиск">
            <X size={17} aria-hidden="true" />
          </button>
        ) : null}
      </span>
      {error ? <span className="place-search__error">{error}</span> : null}
    </label>
  )
}

export const CitySearchBar = SearchBar
