import { Check, ChevronRight, RefreshCw, Search, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { CityOption } from '../../../shared/city/currentCity'
import { cityIdentity, cityLocation, filterCities } from '../model/citySearch'

type Props = {
  cities: CityOption[]
  selectedCity: CityOption
  loading: boolean
  error: string | null
  onClose: () => void
  onRetry: () => void
  onSelect: (city: CityOption) => void
}

export const CityPicker = ({ cities, error, loading, onClose, onRetry, onSelect, selectedCity }: Props) => {
  const [query, setQuery] = useState('')
  const filtered = useMemo(() => filterCities(cities, query), [cities, query])

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [onClose])

  return <div className="city-picker-backdrop" role="presentation" onMouseDown={onClose}>
    <section aria-labelledby="city-picker-title" aria-modal="true" className="city-picker" role="dialog" onMouseDown={(event) => event.stopPropagation()}>
      <span className="city-picker-handle" />
      <header><div><p>CITY GO</p><h2 id="city-picker-title">Найдите город</h2></div>
        <button aria-label="Закрыть" onClick={onClose} type="button"><X size={21} /></button></header>
      <label className="city-picker-search"><Search size={20} /><span className="sr-only">Поиск города, региона или страны</span>
        <input autoComplete="off" autoFocus onChange={(event) => setQuery(event.target.value)} placeholder="Город, регион или страна" type="search" value={query} />
      </label>
      <div className="city-picker-summary"><span>{loading ? 'Обновляем города…' : `${filtered.length} из ${cities.length}`}</span><small>Название · Регион · Страна</small></div>
      <div className="city-picker-list">{filtered.map((city) => <button aria-label={`Выбрать ${cityIdentity(city)}`} className={selectedCity.slug === city.slug ? 'is-active' : ''} key={city.slug} onClick={() => onSelect(city)} type="button">
        <span><strong>{city.name}</strong><small>{cityLocation(city)}</small></span><b>{city.places_count ?? 0}</b>
        {selectedCity.slug === city.slug ? <Check size={19} /> : <ChevronRight size={19} />}
      </button>)}</div>
      {!filtered.length ? <div className="city-picker-empty"><Search size={24} /><strong>Город не найден</strong><p>Проверьте название или попробуйте искать по региону или стране.</p><button onClick={() => setQuery('')} type="button">Сбросить поиск</button></div> : null}
      {error ? <div className="city-picker-error"><span>{error} Текущий город сохранён.</span><button onClick={onRetry} type="button"><RefreshCw size={16} /> Повторить</button></div> : null}
    </section>
  </div>
}
