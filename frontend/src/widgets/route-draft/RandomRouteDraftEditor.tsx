import { useEffect, useMemo, useState } from 'react'
import { addDraftPoint, createRandomDraft, loadCategories, removeDraftPoint, replaceDraftPoint, searchDraftPlaces } from '../../api/routes/routeDraft.api'
import type { CategoryOption, RouteDraft, RouteDraftSearchItem } from '../../api/routes/routeDraft.types'
import {
  filterCategoryOptionsForFeatures,
  filterInterestsForFeatures,
  getUnsupportedInterestLabels,
  interestOptions,
} from '../recommendation-route/chipOptions'

type Props = {
  citySlug: string
  features: string[]
}

const fallbackCategories = interestOptions.map((item) => ({ code: item.value, name: item.label }))

export const RandomRouteDraftEditor = ({ citySlug, features }: Props) => {
  const [categories, setCategories] = useState<CategoryOption[]>(fallbackCategories)
  const [selected, setSelected] = useState<string[]>([])
  const [budget, setBudget] = useState(120)
  const [draft, setDraft] = useState<RouteDraft | null>(null)
  const [query, setQuery] = useState('кофе')
  const [search, setSearch] = useState<RouteDraftSearchItem[]>([])
  const [replacePointId, setReplacePointId] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const visibleCategories = useMemo(
    () => filterCategoryOptionsForFeatures(categories, features),
    [categories, features],
  )
  const unsupportedSelectedLabels = useMemo(
    () => getUnsupportedInterestLabels(selected, features),
    [features, selected],
  )

  useEffect(() => {
    loadCategories().then((items) => {
      if (items.length) setCategories(items.map((item) => ({ code: item.code, name: item.name })))
    }).catch(() => setCategories(fallbackCategories))
  }, [])

  useEffect(() => {
    setSelected((current) => filterInterestsForFeatures(current, features))
    setDraft(null)
    setSearch([])
    setReplacePointId(null)
  }, [citySlug, features])

  const build = async () => {
    const supportedSelected = filterInterestsForFeatures(selected, features)
    await run(async () => {
      setDraft(await createRandomDraft({
        city_slug: citySlug,
        budget_minutes: budget,
        selected_category_slugs: supportedSelected,
        category_mode: supportedSelected.length ? 'balanced' : 'none',
      }))
      setSelected(supportedSelected)
      setSearch([])
    })
  }

  const findPlaces = async () => {
    if (!draft) return
    await run(async () => setSearch(await searchDraftPlaces(draft, query)))
  }

  const mutate = async (operation: Promise<RouteDraft>) => {
    await run(async () => {
      setDraft(await operation)
      setSearch([])
      setReplacePointId(null)
    })
  }

  const run = async (operation: () => Promise<void>) => {
    setBusy(true)
    setError(null)
    try { await operation() } catch { setError('Не удалось обновить random route draft.') } finally { setBusy(false) }
  }

  return (
    <section className="route-config-tile route-draft-editor">
      <header className="route-draft-head">
        <div>
          <p className="route-eyebrow">Random Route MVP</p>
          <h2>Случайный маршрут с быстрым редактированием</h2>
        </div>
        <button type="button" className="route-primary-btn" disabled={busy} onClick={build}>{busy ? 'Собираем...' : 'Случайный маршрут'}</button>
      </header>
      <div className="route-draft-controls">
        <label>Минуты <input value={budget} type="number" min={30} max={480} onChange={(event) => setBudget(Number(event.target.value))} /></label>
        {unsupportedSelectedLabels.length ? (
          <p className="route-start-note">Скрыты неподходящие для города темы: {unsupportedSelectedLabels.join(', ')}.</p>
        ) : null}
        <div className="route-chip-row">{visibleCategories.slice(0, 10).map((item) => (
          <button key={item.code} type="button" className={selected.includes(item.code) ? 'route-chip active' : 'route-chip'} onClick={() => setSelected(toggle(selected, item.code))}>{item.name}</button>
        ))}</div>
      </div>
      {error && <p className="route-error-inline">{error}</p>}
      {draft && (
        <div className="route-draft-result">
          <p><strong>{draft.route_status}</strong> · {draft.total_minutes}/{draft.budget_minutes} мин · mode {draft.category_mode}</p>
          {draft.warnings.map((item) => <p key={item.code} className="route-warning-inline">{item.code}: {item.message}</p>)}
          <ol className="route-draft-points">{draft.points.map((point) => (
            <li key={point.id}>
              <strong>{point.position}. {point.title}</strong><span>{point.category ?? 'без категории'} · {point.visit_minutes} мин</span>
              <button type="button" onClick={() => void mutate(removeDraftPoint(draft, point.id))}>Удалить</button>
              <button type="button" onClick={() => setReplacePointId(point.id)}>Заменить</button>
            </li>
          ))}</ol>
          <div className="route-draft-search">
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="кофе, парк, музей" />
            <button type="button" disabled={busy} onClick={() => void findPlaces()}>Найти место</button>
          </div>
          {search.map((item) => <button key={item.place_id} type="button" className="route-search-row" onClick={() => void mutate(replacePointId ? replaceDraftPoint(draft, replacePointId, item.place_id) : addDraftPoint(draft, item.place_id))}>
              {replacePointId ? 'Заменить на ' : 'Добавить '}{item.title} · {item.category} · {item.fit_reason}
            </button>)}
        </div>
      )}
    </section>
  )
}

const toggle = (items: string[], value: string) => items.includes(value) ? items.filter((item) => item !== value) : [...items, value]
