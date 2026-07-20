import { useEffect, useMemo, useRef, useState } from 'react'
import { MapPinned, Search, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  addDraftPoint,
  createRandomDraft,
  createRouteDraftSessionToken,
  loadCategories,
  removeDraftPoint,
  replaceDraftPoint,
  searchDraftPlaces,
} from '../../api/routes/routeDraft.api'
import type { CategoryOption, RouteDraft, RouteDraftSearchItem } from '../../api/routes/routeDraft.types'
import { buildRandomRoutePlan, nextRandomRouteSeed, type RandomRouteMode, type RandomRoutePlan } from '../../features/routes/model/randomRoutePlan'
import { MapLibreMap } from '../../shared/map/MapLibreMap'
import type { MapPoint } from '../../shared/map/mapTypes'
import {
  filterCategoryOptionsForFeatures,
  interestOptions,
} from '../recommendation-route/chipOptions'
import { RandomRouteModePicker } from './RandomRouteModePicker'

type Props = {
  citySlug: string
  features?: string[]
  initialMode?: RandomRouteMode
}

const EMPTY_FEATURES: string[] = []
const fallbackCategories = interestOptions.map((item) => ({ code: item.value, name: item.label }))

const validDraftMapPoints = (draft: RouteDraft): MapPoint[] => draft.points.flatMap((point) => {
  const latitude = Number(point.lat)
  const longitude = Number(point.lng)
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return []
  if (Math.abs(latitude) > 90 || Math.abs(longitude) > 180 || (latitude === 0 && longitude === 0)) return []
  return [{
    id: point.place_id,
    latitude,
    longitude,
    title: point.title,
    category: point.category,
    order: point.position,
  }]
})

export const RandomRouteDraftEditor = ({ citySlug, features = EMPTY_FEATURES, initialMode = 'random_places' }: Props) => {
  const [categories, setCategories] = useState<CategoryOption[]>(fallbackCategories)
  const [mode, setMode] = useState<RandomRouteMode>(initialMode)
  const [budget, setBudget] = useState(120)
  const [lastPlan, setLastPlan] = useState<RandomRoutePlan | null>(null)
  const [draft, setDraft] = useState<RouteDraft | null>(null)
  const [searchCategory, setSearchCategory] = useState('')
  const [search, setSearch] = useState<RouteDraftSearchItem[]>([])
  const [replacePointId, setReplacePointId] = useState<number | null>(null)
  const [activeMapPointId, setActiveMapPointId] = useState<number | null>(null)
  const [searchMessage, setSearchMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const sessionTokenRef = useRef(createRouteDraftSessionToken())

  const visibleCategories = useMemo(
    () => filterCategoryOptionsForFeatures(categories, features),
    [categories, features],
  )
  const categoryNameByCode = useMemo(
    () => new Map(categories.map((item) => [item.code, item.name])),
    [categories],
  )
  const mapPoints = useMemo(() => draft ? validDraftMapPoints(draft) : [], [draft])
  const replacementPoint = draft?.points.find((point) => point.id === replacePointId) ?? null

  useEffect(() => {
    loadCategories().then((items) => {
      if (items.length) setCategories(items.map((item) => ({ code: item.code, name: item.name })))
    }).catch(() => setCategories(fallbackCategories))
  }, [])

  useEffect(() => {
    sessionTokenRef.current = createRouteDraftSessionToken()
    setDraft(null)
    setLastPlan(null)
    setSearch([])
    setReplacePointId(null)
    setActiveMapPointId(null)
    setSearchCategory('')
    setSearchMessage(null)
  }, [citySlug, features])

  useEffect(() => {
    setMode(initialMode)
    setDraft(null)
    setLastPlan(null)
  }, [initialMode])

  const build = async () => {
    if (!Number.isInteger(budget) || budget < 30 || budget > 480) {
      setError('Продолжительность должна быть от 30 до 480 минут.')
      return
    }
    let plan: RandomRoutePlan
    try {
      plan = buildRandomRoutePlan(mode, visibleCategories.map((item) => item.code), budget, nextRandomRouteSeed())
    } catch (planError) {
      setError(planError instanceof Error ? planError.message : 'Не удалось выбрать случайные параметры.')
      return
    }
    await run(async () => {
      const sessionToken = createRouteDraftSessionToken()
      sessionTokenRef.current = sessionToken
      const nextDraft = await createRandomDraft({
        city_slug: citySlug,
        budget_minutes: plan.minutes,
        selected_category_slugs: plan.categories,
        category_mode: plan.categoryMode,
        seed: plan.seed,
      }, sessionToken)
      setDraft(nextDraft)
      setLastPlan(plan)
      setBudget(plan.minutes)
      setSearch([])
      setSearchMessage(null)
      setActiveMapPointId(nextDraft.points[0]?.place_id ?? null)
    })
  }

  const findPlaces = async () => {
    if (!draft) return
    const category = visibleCategories.find((item) => item.code === searchCategory)
    if (!category) {
      setSearch([])
      setSearchMessage('Сначала выберите категорию места.')
      return
    }
    await run(async () => {
      const items = await searchDraftPlaces(draft, category.name, sessionTokenRef.current)
      setSearch(items.filter((item) => !draft.points.some((point) => point.place_id === item.place_id)))
      setSearchMessage(items.length ? null : 'Подходящих мест этой категории не найдено.')
    })
  }

  const mutate = async (operation: Promise<RouteDraft>) => {
    await run(async () => {
      const nextDraft = await operation
      setDraft(nextDraft)
      setSearch([])
      setReplacePointId(null)
      setSearchMessage(null)
      setActiveMapPointId(nextDraft.points[0]?.place_id ?? null)
    })
  }

  const run = async (operation: () => Promise<void>) => {
    setBusy(true)
    setError(null)
    try { await operation() } catch { setError('Не удалось обновить маршрут. Попробуйте еще раз.') } finally { setBusy(false) }
  }

  const categoryLabel = (category: string | null | undefined) => {
    if (!category) return 'Место'
    return categoryNameByCode.get(category) ?? 'Место'
  }

  const beginReplacement = (pointId: number) => {
    setReplacePointId(pointId)
    setSearch([])
    setSearchMessage('Выберите категорию и подходящее место для замены.')
  }

  return (
    <section className="route-config-tile route-draft-editor">
      <header className="route-draft-head">
        <div>
          <p className="route-eyebrow">Быстрая прогулка</p>
          <h2>Собрать маршрут с быстрым редактированием</h2>
        </div>
        <button type="button" className="route-primary-btn" disabled={busy} onClick={build}>{busy ? 'Собираем...' : mode === 'random_mood' ? 'Удивить меня' : 'Собрать случайные места'}</button>
      </header>
      <RandomRouteModePicker budget={budget} categoriesCount={visibleCategories.length} mode={mode} onBudgetChange={setBudget} onModeChange={(nextMode) => { setMode(nextMode); setDraft(null); setLastPlan(null) }} plan={lastPlan} />
      {error && <p className="route-error-inline">{error}</p>}
      {draft && (
        <div className="route-draft-result">
          <p><strong>{routeStatusLabel(draft.route_status)}</strong> · {draft.total_minutes}/{draft.budget_minutes} мин</p>
          {draft.warnings.map((item) => <p key={item.code} className="route-warning-inline">{item.message}</p>)}
          {mapPoints.length ? (
            <div className="route-draft-map-block">
              <div className="route-draft-map-heading"><MapPinned size={18} /><strong>Маршрут на карте</strong></div>
              <MapLibreMap
                className="route-draft-map"
                points={mapPoints}
                activePointId={activeMapPointId}
                routeLine
                interactiveSelection={false}
                onPointSelect={setActiveMapPointId}
              />
            </div>
          ) : <p className="route-warning-inline">У точек нет корректных координат, поэтому карта пока недоступна.</p>}
          <ol className="route-draft-points">{draft.points.map((point) => (
            <li key={point.id} className={point.place_id === activeMapPointId ? 'is-active' : undefined}>
              <Link to={`/places/${point.slug}`} onClick={() => setActiveMapPointId(point.place_id)}>
                <strong>{point.position}. {point.title}</strong>
                <span>{categoryLabel(point.category)} · {point.visit_minutes} мин</span>
              </Link>
              <div className="route-draft-point-actions">
                <button type="button" disabled={busy} onClick={() => beginReplacement(point.id)}>Заменить</button>
                <button type="button" disabled={busy} onClick={() => void mutate(removeDraftPoint(draft, point.id, sessionTokenRef.current))}>Удалить</button>
              </div>
            </li>
          ))}</ol>
          <div className="route-draft-search-panel">
            <div className="route-draft-search-head">
              <div>
                <strong>{replacementPoint ? `Замена: ${replacementPoint.title}` : 'Добавить место'}</strong>
                <span>Можно выбрать только существующее место из каталога.</span>
              </div>
              {replacementPoint ? <button type="button" className="route-search-cancel" onClick={() => { setReplacePointId(null); setSearch([]); setSearchMessage(null) }}><X size={18} /> Отмена</button> : null}
            </div>
            <div className="route-draft-search">
              <select aria-label="Категория места" value={searchCategory} onChange={(event) => { setSearchCategory(event.target.value); setSearch([]); setSearchMessage(null) }}>
                <option value="">Выберите категорию</option>
                {visibleCategories.map((item) => <option key={item.code} value={item.code}>{item.name}</option>)}
              </select>
              <button type="button" disabled={busy || !searchCategory} onClick={() => void findPlaces()}><Search size={17} /> Показать места</button>
            </div>
            {searchMessage ? <p className="route-search-message">{searchMessage}</p> : null}
            <div className="route-search-results">{search.map((item) => <button key={item.place_id} type="button" className="route-search-row" disabled={busy} onClick={() => void mutate(replacePointId ? replaceDraftPoint(draft, replacePointId, item.place_id, sessionTokenRef.current) : addDraftPoint(draft, item.place_id, sessionTokenRef.current))}>
              <strong>{item.title}</strong>
              <span>{categoryLabel(item.category)}{item.address ? ` · ${item.address}` : ''}</span>
              <small>{replacePointId ? 'Заменить текущую точку' : 'Добавить в конец маршрута'}</small>
            </button>)}</div>
          </div>
        </div>
      )}
    </section>
  )
}

const routeStatusLabel = (status: string) => {
  if (status === 'full') return 'Маршрут собран'
  if (status === 'partial') return 'Маршрут собран частично'
  return 'Маршрут пока не собран'
}
