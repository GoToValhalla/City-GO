import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import type {
  AutomationPreviewResponse,
  CriticalCoverageIssue,
  CriticalCoveragePlacesResponse,
  CriticalCoverageRefreshResponse,
  DuplicateGroup,
  DuplicateGroupsResponse,
  PipelineRunResponse,
  QualityCity,
} from './adminPlatformTypes'
import { AdminEmpty, AdminError, AdminLoading, AdminSectionError } from './shared/AdminStates'
import './AdminQuality.css'

const BLOCKER_LABELS: Record<string, string> = {
  no_photo: 'без фото',
  no_address: 'без адреса',
  low_quality: 'низкое качество',
  stale: 'перепроверка',
  route_ineligible: 'исключены из маршрутов',
  excluded_by_design: 'исключено правилами',
}

const BUCKET_LABELS: Record<string, string> = {
  route_blocker: 'Блокеры',
  card_blocker: 'Карточки',
  auto_enrichment_candidate: 'Авто',
  manual_review: 'Проверка',
  optional_gap: 'Пробелы',
  not_applicable: 'Не маршрут',
}

const STATUS_LABELS: Record<string, string> = {
  route_blocker: 'блокер',
  route_ready: 'готов',
  route_excluded: 'исключён',
  card_blocker: 'блокер',
  card_ready: 'готова',
  optional_gap: 'не критично',
  not_applicable: 'не применимо',
}

type BulkActionResponse = {
  action_type: string
  affected_count: number
  created_candidates?: number | null
  status?: string | null
}

const safeCount = (value: unknown) => (
  typeof value === 'number' && Number.isFinite(value) ? Math.max(0, value) : 0
)

const qualityStats = (item: QualityCity) => {
  const reviewTotal = safeCount(item.review_universe_total ?? item.places_total)
  const manualTotal = Math.min(safeCount(item.manual_review_total), reviewTotal)
  const excludedTotal = safeCount(item.auto_excluded_total ?? item.blockers.excluded_by_design)
  return { reviewTotal, manualTotal, excludedTotal }
}

const criticalStats = (item: QualityCity) => ({
  routeReady: safeCount(item.route_ready_total),
  routeCandidates: safeCount(item.route_candidate_total),
  routeBlockers: safeCount(item.route_blockers_total),
  cardBlockers: safeCount(item.card_blockers_total),
  autoEnrichment: safeCount(item.auto_enrichment_total),
  manualReview: safeCount(item.critical_manual_review_total),
})

const coveragePct = (item: QualityCity, key: string) => {
  const metric = item.critical_coverage?.coverage?.[key]
  return typeof metric?.pct === 'number' ? `${metric.pct}%` : '—'
}

const primaryBlockerText = (item: QualityCity) => {
  const key = item.primary_blocker
  if (!key) return 'Ручных блокеров нет'
  return `Главное: ${BLOCKER_LABELS[key] ?? key} (${item.blockers[key] ?? 0})`
}

const blockerLine = (item: QualityCity) => [
  ['no_photo', item.blockers.no_photo ?? 0],
  ['no_address', item.blockers.no_address ?? 0],
  ['low_quality', item.blockers.low_quality ?? 0],
  ['stale', item.blockers.stale ?? 0],
]
  .filter(([, value]) => Number(value) > 0)
  .slice(0, 3)
  .map(([key, value]) => `${BLOCKER_LABELS[String(key)] ?? key}: ${value}`)
  .join(' · ')

const automationStatusText = (preview: AutomationPreviewResponse) => {
  const affected = safeCount(preview.affected_count)
  const blocked = safeCount(preview.blocked_count)
  if (affected > 0) return `Можно применить: ${affected} · заблокировано guardrail: ${blocked}`
  if (blocked > 0) return `Безопасных автоисправлений нет · заблокировано guardrail: ${blocked}`
  return 'Безопасных автоисправлений сейчас нет: stoplist уже исключён или нужен refresh качества.'
}

const duplicateTitle = (group: DuplicateGroup) => group.title || group.normalized_title || 'Без названия'

const qualityQuery = (params: URLSearchParams) => {
  const next = new URLSearchParams(params)
  next.delete('critical_bucket')
  next.delete('critical_reason')
  return next.toString()
}

const duplicateQuery = (citySlug: string) => {
  const next = new URLSearchParams()
  next.set('city_slug', citySlug)
  next.set('limit', '5')
  return next.toString()
}

const criticalDrilldownPath = (params: URLSearchParams) => {
  const citySlug = params.get('city_slug')
  const bucket = params.get('critical_bucket')
  if (!citySlug || !bucket) return null
  const query = new URLSearchParams()
  query.set('bucket', bucket)
  const reason = params.get('critical_reason')
  const category = params.get('category')
  if (reason) query.set('reason', reason)
  if (category) query.set('category', category)
  query.set('limit', '50')
  return `/admin/data-quality/cities/${citySlug}/critical-coverage/places?${query}`
}

const automationPayload = (citySlug: string) => ({ city_slug: citySlug, limit: 500 })

const emptyDuplicateResponse = { items: [], total: 0, limit: 5, offset: 0 }
const emptyAutomationResponse: AutomationPreviewResponse = {
  action_type: 'auto_exclude_stoplist_from_routes',
  affected_count: 0,
  blocked_count: 0,
  status: 'preview',
}

const safeDuplicateItems = (payload: Partial<DuplicateGroupsResponse> | null | undefined): DuplicateGroup[] => (
  Array.isArray(payload?.items) ? payload.items : []
)

const safeDuplicateTotal = (payload: Partial<DuplicateGroupsResponse> | null | undefined, items: DuplicateGroup[]) => (
  typeof payload?.total === 'number' ? payload.total : items.length
)

const safeAutomation = (payload: Partial<AutomationPreviewResponse> | null | undefined): AutomationPreviewResponse => ({
  action_type: typeof payload?.action_type === 'string' ? payload.action_type : emptyAutomationResponse.action_type,
  affected_count: typeof payload?.affected_count === 'number' ? payload.affected_count : 0,
  blocked_count: typeof payload?.blocked_count === 'number' ? payload.blocked_count : 0,
  candidate_ids: Array.isArray(payload?.candidate_ids) ? payload.candidate_ids : null,
  sample: Array.isArray(payload?.sample) ? payload.sample : null,
  blocked_sample: Array.isArray(payload?.blocked_sample) ? payload.blocked_sample : null,
  grouped_by_city: payload?.grouped_by_city ?? null,
  grouped_by_category: payload?.grouped_by_category ?? null,
  warnings: Array.isArray(payload?.warnings) ? payload.warnings : null,
  proposed_patch: payload?.proposed_patch ?? null,
  status: payload?.status ?? 'preview',
})

const actionCopy: Record<string, { reason: string; done: string }> = {
  propose_duplicate_review: {
    reason: 'ручная проверка дубля',
    done: 'Группа поставлена в ручную проверку.',
  },
  ignore_issues: {
    reason: 'проверено, это разные места',
    done: 'Группа скрыта из активных дублей как не дубль.',
  },
  defer_issues: {
    reason: 'отложено до ручной проверки источников',
    done: 'Группа отложена.',
  },
}

const issueText = (items: CriticalCoverageIssue[]) => (
  items.length ? items.map((item) => `${item.field_name}: ${item.reason}`).join(' · ') : 'Нет'
)

const statusText = (value: string) => STATUS_LABELS[value] ?? value

export const AdminQualityPage = () => {
  const [params, setParams] = useSearchParams()
  const selectedCitySlug = params.get('city_slug') ?? ''
  const currentQualityQuery = qualityQuery(params)
  const currentDrilldownPath = criticalDrilldownPath(params)
  const [items, setItems] = useState<QualityCity[]>([])
  const [todo, setTodo] = useState<string[]>([])
  const [automationPreview, setAutomationPreview] = useState<AutomationPreviewResponse>(emptyAutomationResponse)
  const [duplicateGroups, setDuplicateGroups] = useState<DuplicateGroup[]>([])
  const [duplicateTotal, setDuplicateTotal] = useState(0)
  const [criticalPlaces, setCriticalPlaces] = useState<CriticalCoveragePlacesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [operationsLoading, setOperationsLoading] = useState(false)
  const [criticalLoading, setCriticalLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [automationMessage, setAutomationMessage] = useState<string | null>(null)
  const [duplicateMessage, setDuplicateMessage] = useState<string | null>(null)
  const [criticalMessage, setCriticalMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [operationsError, setOperationsError] = useState<string | null>(null)
  const [criticalError, setCriticalError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const row = await adminGet<{ items: QualityCity[]; todo: string[] }>(`/admin/quality?${currentQualityQuery}`)
      setItems(Array.isArray(row.items) ? row.items : [])
      setTodo(Array.isArray(row.todo) ? row.todo : [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось загрузить качество')
    } finally {
      setLoading(false)
    }
  }, [currentQualityQuery])

  const loadOperations = useCallback(async () => {
    setOperationsError(null)
    if (!selectedCitySlug) {
      setAutomationPreview(emptyAutomationResponse)
      setDuplicateGroups([])
      setDuplicateTotal(0)
      return
    }
    setOperationsLoading(true)
    try {
      const [automation, duplicates] = await Promise.all([
        adminPost<Partial<AutomationPreviewResponse>>(
          '/admin/data-quality/automation/preview',
          automationPayload(selectedCitySlug),
          { invalidateCache: false },
        ).catch(() => emptyAutomationResponse),
        adminGet<Partial<DuplicateGroupsResponse>>(`/admin/data-quality/duplicates?${duplicateQuery(selectedCitySlug)}`)
          .catch(() => emptyDuplicateResponse),
      ])
      const duplicateItems = safeDuplicateItems(duplicates)
      setAutomationPreview(safeAutomation(automation))
      setDuplicateGroups(duplicateItems)
      setDuplicateTotal(safeDuplicateTotal(duplicates, duplicateItems))
    } catch (e) {
      setOperationsError(e instanceof Error ? e.message : 'Не удалось загрузить действия')
    } finally {
      setOperationsLoading(false)
    }
  }, [selectedCitySlug])

  const loadCritical = useCallback(async () => {
    setCriticalError(null)
    if (!currentDrilldownPath) {
      setCriticalPlaces(null)
      return
    }
    setCriticalLoading(true)
    try {
      setCriticalPlaces(await adminGet<CriticalCoveragePlacesResponse>(currentDrilldownPath))
    } catch (e) {
      setCriticalPlaces(null)
      setCriticalError(e instanceof Error ? e.message : 'Не удалось загрузить места')
    } finally {
      setCriticalLoading(false)
    }
  }, [currentDrilldownPath])

  useEffect(() => { void load() }, [load])
  useEffect(() => { void loadOperations() }, [loadOperations])
  useEffect(() => { void loadCritical() }, [loadCritical])

  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    next.delete('critical_bucket')
    next.delete('critical_reason')
    setParams(next)
  }
  const openCritical = (citySlug: string, bucket: string, reason?: string) => {
    const next = new URLSearchParams(params)
    next.set('city_slug', citySlug)
    next.set('critical_bucket', bucket)
    if (reason) next.set('critical_reason', reason)
    else next.delete('critical_reason')
    setParams(next)
  }
  const closeCritical = () => {
    const next = new URLSearchParams(params)
    next.delete('critical_bucket')
    next.delete('critical_reason')
    setParams(next)
  }
  const applyAutomation = async () => {
    if (!selectedCitySlug) return
    setActionLoading('automation')
    setAutomationMessage(null)
    try {
      const result = await adminPost<AutomationPreviewResponse>('/admin/data-quality/automation/apply', {
        ...automationPayload(selectedCitySlug),
        confirm: true,
        reason: 'safe stoplist route exclusion from admin quality page',
      })
      setAutomationMessage(`Автопилот применён. Из маршрутов исключено: ${result.affected_count}.`)
      void load()
      void loadOperations()
    } catch (e) {
      setAutomationMessage(e instanceof Error ? e.message : 'Не удалось применить автопилот')
    } finally {
      setActionLoading(null)
    }
  }
  const runCityPipeline = async (citySlug: string) => {
    setActionLoading(`pipeline:${citySlug}`)
    setCriticalMessage(null)
    try {
      const result = await adminPost<PipelineRunResponse>(`/admin/place-enrichment/pipeline/${citySlug}/run`)
      setCriticalMessage(`Обогащение в очереди: job #${result.job_id}.`)
      void load()
      void loadOperations()
    } catch (e) {
      setCriticalMessage(e instanceof Error ? e.message : 'Не удалось запустить обогащение')
    } finally {
      setActionLoading(null)
    }
  }
  const materializeCity = async (citySlug: string) => {
    setActionLoading(`materialize:${citySlug}`)
    setCriticalMessage(null)
    try {
      const result = await adminPost<CriticalCoverageRefreshResponse>(`/admin/data-quality/cities/${citySlug}/critical-coverage/refresh`)
      setCriticalMessage(`Снимок: +${result.created}, обновлено ${result.updated}, без изменений ${result.unchanged}.`)
      void load()
      void loadCritical()
    } catch (e) {
      setCriticalMessage(e instanceof Error ? e.message : 'Не удалось сохранить снимок')
    } finally {
      setActionLoading(null)
    }
  }
  const applyDuplicateAction = async (group: DuplicateGroup, actionType: keyof typeof actionCopy) => {
    const copy = actionCopy[actionType]
    setActionLoading(`${actionType}:${group.group_key}`)
    setDuplicateMessage(null)
    try {
      const result = await adminPost<BulkActionResponse>('/admin/data-quality/bulk-actions/apply', {
        action_type: actionType,
        issue_ids: group.issue_ids,
        confirm: true,
        reason: copy.reason,
      })
      setDuplicateMessage(`${copy.done} Затронуто: ${result.affected_count}.`)
      void loadOperations()
    } catch (e) {
      setDuplicateMessage(e instanceof Error ? e.message : 'Не удалось применить действие')
    } finally {
      setActionLoading(null)
    }
  }
  return <div className="admin-quality-page">
    <h2 className="admin-page-title">Качество</h2>
    <p className="admin-page-subtitle">Покрытие и блокеры по городам.</p>
    <div className="admin-filter-card admin-filter-grid admin-quality-filter-card">
      <label className="admin-field"><span>Город</span><input value={selectedCitySlug} onChange={(e) => update('city_slug', e.target.value)} /></label>
      <label className="admin-field"><span>Регион</span><input value={params.get('region') ?? ''} onChange={(e) => update('region', e.target.value)} /></label>
      <label className="admin-field"><span>Категория</span><input value={params.get('category') ?? ''} onChange={(e) => update('category', e.target.value)} /></label>
      <label className="admin-field"><span>Важность</span><select value={params.get('severity') ?? ''} onChange={(e) => update('severity', e.target.value)}><option value="">Любая</option><option value="critical">Критично</option><option value="warning">Внимание</option><option value="ok">Норма</option></select></label>
    </div>
    {criticalMessage && <p className="admin-muted">{criticalMessage}</p>}
    {error && <AdminError message={error} />}{loading ? <AdminLoading /> : !items.length ? <AdminEmpty message="Нет данных по выбранным фильтрам" /> : <div className="admin-action-grid admin-quality-grid">{items.map((item) => {
      const details = blockerLine(item)
      const stats = qualityStats(item)
      const critical = criticalStats(item)
      return <article className={`admin-action-card admin-quality-card admin-severity-${item.severity === 'critical' ? 'red' : item.severity === 'warning' ? 'yellow' : 'green'}`} key={item.city_slug}>
        <Link to={`/admin/cities/${item.city_slug}?tab=quality`}><strong className="admin-quality-card-title">{item.city_name}</strong></Link>
        <div className="admin-action-count">{item.readiness_score}%</div>
        <span className="admin-quality-total">{item.places_total} мест всего</span>
        <div className="admin-quality-lines">
          <span>К проверке: {stats.manualTotal} из {stats.reviewTotal}</span>
          <span>Туристических: {stats.reviewTotal} · исключено: {stats.excludedTotal}</span>
          <span>{primaryBlockerText(item)}</span>
          {details && <span>{details}</span>}
        </div>
        {item.critical_coverage && <>
          <div className="admin-quality-tabs" aria-label={`Вкладки качества ${item.city_name}`}>
            <button type="button" className="admin-quality-tab" onClick={() => openCritical(item.city_slug, 'route_blocker')}><span>Блокеры</span><strong>{critical.routeBlockers}</strong></button>
            <button type="button" className="admin-quality-tab" onClick={() => openCritical(item.city_slug, 'card_blocker')}><span>Карточки</span><strong>{critical.cardBlockers}</strong></button>
            <button type="button" className="admin-quality-tab" onClick={() => openCritical(item.city_slug, 'auto_enrichment_candidate')}><span>Авто</span><strong>{critical.autoEnrichment}</strong></button>
            <button type="button" className="admin-quality-tab" onClick={() => openCritical(item.city_slug, 'manual_review')}><span>Проверка</span><strong>{critical.manualReview}</strong></button>
          </div>
          <div className="admin-quality-coverage">
            <span>Маршрут: {critical.routeReady}/{critical.routeCandidates}</span>
            <span>Фото {coveragePct(item, 'has_approved_photo')} · часы {coveragePct(item, 'has_opening_hours')}</span>
            <span>Адреса {coveragePct(item, 'has_address')} · описания {coveragePct(item, 'has_description')}</span>
          </div>
        </>}
        <div className="admin-quality-actions" aria-label={`Действия ${item.city_name}`}>
          <button type="button" className="admin-btn admin-btn-sm" title="Запустить обогащение" disabled={actionLoading !== null || critical.autoEnrichment <= 0} onClick={() => void runCityPipeline(item.city_slug)}>{actionLoading === `pipeline:${item.city_slug}` ? 'Запуск...' : 'Обогащение'}</button>
          <Link className="admin-btn admin-btn-sm" to={`/admin/photos?city=${item.city_slug}`}>Фото</Link>
          <Link className="admin-btn admin-btn-sm" to={`/admin/enrichment?city=${item.city_slug}`}>Очередь</Link>
          <button type="button" className="admin-btn admin-btn-sm" title="Сохранить снимок качества" disabled={actionLoading !== null} onClick={() => void materializeCity(item.city_slug)}>{actionLoading === `materialize:${item.city_slug}` ? 'Сохр...' : 'Снимок'}</button>
        </div>
      </article>
    })}</div>}
    {!loading && !error && criticalLoading && <section className="admin-card admin-quality-drilldown"><AdminLoading message="Гружу места…" /></section>}
    {!loading && !error && criticalError && <AdminSectionError title="Не удалось загрузить места" message={criticalError} onRetry={() => void loadCritical()} />}
    {!loading && !error && !criticalLoading && criticalPlaces && <section className="admin-card admin-quality-drilldown">
      <div className="admin-quality-drilldown-head"><strong>{BUCKET_LABELS[criticalPlaces.bucket ?? ''] ?? criticalPlaces.bucket}: {criticalPlaces.city_name}</strong><button type="button" className="admin-btn admin-btn-sm" onClick={closeCritical}>Назад</button></div>
      <p className="admin-muted">Показано {criticalPlaces.items.length} из {criticalPlaces.total}{criticalPlaces.reason ? ` · ${criticalPlaces.reason}` : ''}</p>
      {!criticalPlaces.items.length ? <AdminEmpty message="Мест по выбранной вкладке нет" /> : <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Место</th><th>Статус</th><th>Проблемы</th><th>Действия</th></tr></thead><tbody>{criticalPlaces.items.map((row) => <tr key={row.place.id}>
        <td data-label="Место"><Link to={`/admin/places/${row.place.id}`}>{row.place.title}</Link><br /><span className="admin-muted">{row.place.category ?? row.place.canonical_category ?? row.profile_key}</span></td>
        <td data-label="Статус">Маршрут: {statusText(row.route_status)}<br />Карточка: {statusText(row.card_status)}</td>
        <td data-label="Проблемы"><span>{issueText(row.route_blockers)}</span><br /><span>{issueText(row.card_blockers)}</span><br />{row.manual_review_items.length > 0 && <span>Проверка: {issueText(row.manual_review_items)}</span>}</td>
        <td data-label="Действия"><Link className="admin-btn admin-btn-sm" to={`/admin/places/${row.place.id}`}>Место</Link>{row.auto_enrichment_candidates.length > 0 && <Link className="admin-btn admin-btn-sm" to={`/admin/enrichment?city=${criticalPlaces.city_slug}`}>Обогащение</Link>}{row.manual_review_items.length > 0 && <Link className="admin-btn admin-btn-sm" to={`/admin/enrichment?city=${criticalPlaces.city_slug}`}>Проверка</Link>}</td>
      </tr>)}</tbody></table></div>}
    </section>}
    {!loading && !error && selectedCitySlug && <section className="admin-card admin-quality-autopilot">
      <strong>Безопасный автопилот</strong>
      {operationsLoading ? <AdminLoading message="Гружу действия…" /> : operationsError ? <AdminSectionError title="Не удалось загрузить действия" message={operationsError} onRetry={() => void loadOperations()} /> : <>
        <p className="admin-muted">Исключает из маршрутов только очевидные stoplist категории. Публикацию и данные места не трогает.</p>
        <p className="admin-muted">{automationStatusText(automationPreview)}</p>
        {automationPreview.warnings?.map((warning) => <p key={warning} className="admin-muted">{warning}</p>)}
        {automationMessage && <p className="admin-muted">{automationMessage}</p>}
        <button type="button" className="admin-btn" disabled={actionLoading !== null || automationPreview.affected_count <= 0} onClick={() => void applyAutomation()}>
          {actionLoading === 'automation' ? 'Применяю...' : 'Автоисправить'}
        </button>
      </>}
    </section>}
    {!loading && !error && selectedCitySlug && <section className="admin-card">
      <strong>Возможные дубли</strong>
      {operationsLoading ? <AdminLoading message="Гружу дубли…" /> : operationsError ? <AdminSectionError title="Не удалось загрузить дубли" message={operationsError} onRetry={() => void loadOperations()} /> : <>
        <p className="admin-muted">Группы с одинаковым названием рядом. Merge/delete выполняется вручную после проверки.</p>
        {duplicateMessage && <p className="admin-muted">{duplicateMessage}</p>}
        {duplicateTotal === 0 ? <p className="admin-muted">Активных дублей по выбранному городу нет.</p> : <div className="admin-table-wrap"><table className="admin-table">
          <thead><tr><th>Город</th><th>Название</th><th>Места</th><th>Открыть</th><th>Действия</th></tr></thead>
          <tbody>{duplicateGroups.map((group) => {
            const places = Array.isArray(group.places) ? group.places : []
            const actionKey = (actionType: string) => `${actionType}:${group.group_key}`
            return <tr key={group.group_key}>
              <td data-label="Город">{group.city_name ?? group.city_slug ?? '—'}</td>
              <td data-label="Название">{duplicateTitle(group)}<br /><span className="admin-muted">issues: {group.issues_count}</span></td>
              <td data-label="Места">{places.map((place) => place.title).join(' · ')}</td>
              <td data-label="Открыть">{places.map((place) => <Link key={place.id} className="admin-btn admin-btn-sm" to={`/admin/places/${place.id}`}>#{place.id}</Link>)}</td>
              <td data-label="Действия">
                <button type="button" className="admin-btn admin-btn-sm" disabled={actionLoading !== null} onClick={() => void applyDuplicateAction(group, 'propose_duplicate_review')}>
                  {actionLoading === actionKey('propose_duplicate_review') ? 'Ставлю...' : 'В проверку'}
                </button>
                <button type="button" className="admin-btn admin-btn-sm" disabled={actionLoading !== null} onClick={() => void applyDuplicateAction(group, 'ignore_issues')}>
                  {actionLoading === actionKey('ignore_issues') ? 'Скрываю...' : 'Не дубль'}
                </button>
                <button type="button" className="admin-btn admin-btn-sm" disabled={actionLoading !== null} onClick={() => void applyDuplicateAction(group, 'defer_issues')}>
                  {actionLoading === actionKey('defer_issues') ? 'Откладываю...' : 'Отложить'}
                </button>
              </td>
            </tr>
          })}</tbody>
        </table></div>}
        {duplicateTotal > duplicateGroups.length && <p className="admin-muted">Показаны первые {duplicateGroups.length} из {duplicateTotal}. Уточните город, чтобы разобрать очередь.</p>}
      </>}
    </section>}
    {!loading && !error && todo.length > 0 && <section className="admin-help-panel"><strong>Следующий этап</strong><ul>{todo.map((text) => <li key={text}>{text}</li>)}</ul></section>}
  </div>
}