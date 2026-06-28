import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import type { AutomationPreviewResponse, DuplicateGroup, DuplicateGroupsResponse, QualityCity } from './adminPlatformTypes'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

const BLOCKER_LABELS: Record<string, string> = {
  no_photo: 'без фото',
  no_address: 'без адреса',
  low_quality: 'низкое качество',
  stale: 'перепроверка',
  route_ineligible: 'исключены из маршрутов',
  excluded_by_design: 'исключено правилами',
}

type BulkActionResponse = {
  action_type: string
  affected_count: number
  created_candidates?: number | null
  status?: string | null
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

const routeUniverseLine = (item: QualityCity) => {
  const reviewTotal = item.review_universe_total ?? item.places_total
  const manualTotal = item.manual_review_total ?? 0
  const excludedTotal = item.auto_excluded_total ?? item.blockers.excluded_by_design ?? 0
  return `К ручной проверке: ${manualTotal} из ${reviewTotal} туристических кандидатов · исключено правилами: ${excludedTotal}`
}

const duplicateTitle = (group: DuplicateGroup) => group.title || group.normalized_title || 'Без названия'

const duplicateQuery = (params: URLSearchParams) => {
  const next = new URLSearchParams()
  const citySlug = params.get('city_slug')
  if (citySlug) next.set('city_slug', citySlug)
  next.set('limit', '5')
  return next.toString()
}

const automationPayload = (params: URLSearchParams) => {
  const citySlug = params.get('city_slug')
  return { ...(citySlug ? { city_slug: citySlug } : {}), limit: 500 }
}

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

export const AdminQualityPage = () => {
  const [params, setParams] = useSearchParams()
  const [items, setItems] = useState<QualityCity[]>([])
  const [todo, setTodo] = useState<string[]>([])
  const [automationPreview, setAutomationPreview] = useState<AutomationPreviewResponse>(emptyAutomationResponse)
  const [duplicateGroups, setDuplicateGroups] = useState<DuplicateGroup[]>([])
  const [duplicateTotal, setDuplicateTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const load = useCallback(() => {
    setLoading(true); setError(null)
    Promise.all([
      adminGet<{ items: QualityCity[]; todo: string[] }>(`/admin/quality?${params}`),
      adminPost<Partial<AutomationPreviewResponse>>('/admin/data-quality/automation/preview', automationPayload(params))
        .catch(() => emptyAutomationResponse),
      adminGet<Partial<DuplicateGroupsResponse>>(`/admin/data-quality/duplicates?${duplicateQuery(params)}`)
        .catch(() => emptyDuplicateResponse),
    ])
      .then(([row, automation, duplicates]) => {
        const duplicateItems = safeDuplicateItems(duplicates)
        setItems(Array.isArray(row.items) ? row.items : [])
        setTodo(Array.isArray(row.todo) ? row.todo : [])
        setAutomationPreview(safeAutomation(automation))
        setDuplicateGroups(duplicateItems)
        setDuplicateTotal(safeDuplicateTotal(duplicates, duplicateItems))
      })
      .catch((e: Error) => setError(e.message)).finally(() => setLoading(false))
  }, [params])
  useEffect(() => { void Promise.resolve().then(load) }, [load])
  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next)
  }
  const applyAutomation = async () => {
    setActionLoading('automation')
    setActionMessage(null)
    try {
      const result = await adminPost<AutomationPreviewResponse>('/admin/data-quality/automation/apply', {
        ...automationPayload(params),
        confirm: true,
        reason: 'safe stoplist route exclusion from admin quality page',
      })
      setActionMessage(`Автопилот применён. Из маршрутов исключено: ${result.affected_count}.`)
      load()
    } catch (e) {
      setActionMessage(e instanceof Error ? e.message : 'Не удалось применить автопилот')
    } finally {
      setActionLoading(null)
    }
  }
  const applyDuplicateAction = async (group: DuplicateGroup, actionType: keyof typeof actionCopy) => {
    const copy = actionCopy[actionType]
    setActionLoading(`${actionType}:${group.group_key}`)
    setActionMessage(null)
    try {
      const result = await adminPost<BulkActionResponse>('/admin/data-quality/bulk-actions/apply', {
        action_type: actionType,
        issue_ids: group.issue_ids,
        confirm: true,
        reason: copy.reason,
      })
      setActionMessage(`${copy.done} Затронуто: ${result.affected_count}.`)
      load()
    } catch (e) {
      setActionMessage(e instanceof Error ? e.message : 'Не удалось применить действие')
    } finally {
      setActionLoading(null)
    }
  }
  return <div>
    <h2 className="admin-page-title">Качество данных</h2>
    <p className="admin-page-subtitle">Live score считает ручную проверку по туристическим кандидатам. Аптеки, банки, остановки и сервисные POI исключаются правилами и не раздувают очередь.</p>
    <div className="admin-filter-card admin-filter-grid">
      <label className="admin-field"><span>Город</span><input value={params.get('city_slug') ?? ''} onChange={(e) => update('city_slug', e.target.value)} /></label>
      <label className="admin-field"><span>Регион</span><input value={params.get('region') ?? ''} onChange={(e) => update('region', e.target.value)} /></label>
      <label className="admin-field"><span>Категория</span><input value={params.get('category') ?? ''} onChange={(e) => update('category', e.target.value)} /></label>
      <label className="admin-field"><span>Важность</span><select value={params.get('severity') ?? ''} onChange={(e) => update('severity', e.target.value)}><option value="">Любая</option><option value="critical">Критично</option><option value="warning">Внимание</option><option value="ok">Норма</option></select></label>
    </div>
    {error && <AdminError message={error} />}{loading ? <AdminLoading /> : !items.length ? <AdminEmpty message="Нет данных по выбранным фильтрам" /> : <div className="admin-action-grid">{items.map((item) => {
      const details = blockerLine(item)
      return <Link className={`admin-action-card admin-severity-${item.severity === 'critical' ? 'red' : item.severity === 'warning' ? 'yellow' : 'green'}`} to={`/admin/cities/${item.city_slug}?tab=quality`} key={item.city_slug}>
        <strong>{item.city_name}</strong>
        <div className="admin-action-count">{item.readiness_score}%</div>
        <span>{item.places_total} мест</span>
        <span className="admin-muted">{routeUniverseLine(item)}</span>
        <span className="admin-muted">{primaryBlockerText(item)}</span>
        {details && <span className="admin-muted">{details}</span>}
      </Link>
    })}</div>}
    {!loading && !error && <section className="admin-card">
      <strong>Безопасный автопилот</strong>
      <p className="admin-muted">Автоматически исключает из маршрутов только очевидные stoplist категории. Публикацию и данные места не трогает, откат доступен по созданным candidates.</p>
      <p className="admin-muted">Можно применить: {automationPreview.affected_count} · заблокировано guardrail: {automationPreview.blocked_count ?? 0}</p>
      {automationPreview.warnings?.map((warning) => <p key={warning} className="admin-muted">{warning}</p>)}
      <button type="button" className="admin-btn" disabled={actionLoading !== null || automationPreview.affected_count <= 0} onClick={() => void applyAutomation()}>
        {actionLoading === 'automation' ? 'Применяю...' : 'Автоисправить безопасное'}
      </button>
    </section>}
    {!loading && !error && <section className="admin-card">
      <strong>Возможные дубли</strong>
      <p className="admin-muted">Группы с одинаковым названием рядом. Система только показывает кандидатов, merge/delete выполняется вручную после проверки.</p>
      {actionMessage && <p className="admin-muted">{actionMessage}</p>}
      {duplicateTotal === 0 ? <p className="admin-muted">Активных дублей по выбранному городу нет.</p> : <table className="admin-table">
        <thead><tr><th>Город</th><th>Название</th><th>Места</th><th>Открыть</th><th>Действия</th></tr></thead>
        <tbody>{duplicateGroups.map((group) => {
          const places = Array.isArray(group.places) ? group.places : []
          const actionKey = (actionType: string) => `${actionType}:${group.group_key}`
          return <tr key={group.group_key}>
            <td>{group.city_name ?? group.city_slug ?? '—'}</td>
            <td>{duplicateTitle(group)}<br /><span className="admin-muted">issues: {group.issues_count}</span></td>
            <td>{places.map((place) => place.title).join(' · ')}</td>
            <td>{places.map((place) => <Link key={place.id} className="admin-btn admin-btn-sm" to={`/admin/places/${place.id}`}>#{place.id}</Link>)}</td>
            <td>
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
      </table>}
      {duplicateTotal > duplicateGroups.length && <p className="admin-muted">Показаны первые {duplicateGroups.length} из {duplicateTotal}. Уточните город, чтобы разобрать очередь.</p>}
    </section>}
    <section className="admin-help-panel"><strong>Следующий этап</strong><ul>{todo.map((text) => <li key={text}>{text}</li>)}</ul></section>
  </div>
}
