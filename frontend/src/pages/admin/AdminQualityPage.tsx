import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet } from './adminApi'
import type { DuplicateGroup, DuplicateGroupsResponse, QualityCity } from './adminPlatformTypes'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

const BLOCKER_LABELS: Record<string, string> = {
  no_photo: 'без фото',
  no_address: 'без адреса',
  low_quality: 'низкое качество',
  stale: 'перепроверка',
  route_ineligible: 'исключены из маршрутов',
}

const primaryBlockerText = (item: QualityCity) => {
  const key = item.primary_blocker
  if (!key) return 'Критичных блокеров нет'
  return `Главное: ${BLOCKER_LABELS[key] ?? key} (${item.blockers[key] ?? 0})`
}

const blockerLine = (item: QualityCity) => [
  ['no_photo', item.blockers.no_photo ?? 0],
  ['no_address', item.blockers.no_address ?? 0],
  ['low_quality', item.blockers.low_quality ?? 0],
  ['stale', item.blockers.stale ?? 0],
  ['route_ineligible', item.blockers.route_ineligible ?? 0],
]
  .filter(([, value]) => Number(value) > 0)
  .slice(0, 3)
  .map(([key, value]) => `${BLOCKER_LABELS[String(key)] ?? key}: ${value}`)
  .join(' · ')

const duplicateTitle = (group: DuplicateGroup) => group.title || group.normalized_title || 'Без названия'

const duplicateQuery = (params: URLSearchParams) => {
  const next = new URLSearchParams()
  const citySlug = params.get('city_slug')
  if (citySlug) next.set('city_slug', citySlug)
  next.set('limit', '5')
  return next.toString()
}

export const AdminQualityPage = () => {
  const [params, setParams] = useSearchParams()
  const [items, setItems] = useState<QualityCity[]>([])
  const [todo, setTodo] = useState<string[]>([])
  const [duplicateGroups, setDuplicateGroups] = useState<DuplicateGroup[]>([])
  const [duplicateTotal, setDuplicateTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const load = useCallback(() => {
    setLoading(true); setError(null)
    Promise.all([
      adminGet<{ items: QualityCity[]; todo: string[] }>(`/admin/quality?${params}`),
      adminGet<DuplicateGroupsResponse>(`/admin/data-quality/duplicates?${duplicateQuery(params)}`),
    ])
      .then(([row, duplicates]) => {
        setItems(row.items)
        setTodo(row.todo)
        setDuplicateGroups(duplicates.items)
        setDuplicateTotal(duplicates.total)
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
  return <div>
    <h2 className="admin-page-title">Качество данных</h2>
    <p className="admin-page-subtitle">Live score считается по текущим блокерам: фото, адреса, низкое качество и перепроверка. Исключённые из маршрутов показаны отдельно и не штрафуют город.</p>
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
        <span className="admin-muted">{primaryBlockerText(item)}</span>
        {details && <span className="admin-muted">{details}</span>}
      </Link>
    })}</div>}
    {!loading && !error && <section className="admin-card">
      <strong>Возможные дубли</strong>
      <p className="admin-muted">Группы с одинаковым названием рядом. Система только показывает кандидатов, merge/delete выполняется вручную после проверки.</p>
      {duplicateTotal === 0 ? <p className="admin-muted">Активных дублей по выбранному городу нет.</p> : <table className="admin-table">
        <thead><tr><th>Город</th><th>Название</th><th>Места</th><th>Открыть</th></tr></thead>
        <tbody>{duplicateGroups.map((group) => (
          <tr key={group.group_key}>
            <td>{group.city_name ?? group.city_slug ?? '—'}</td>
            <td>{duplicateTitle(group)}</td>
            <td>{group.places.map((place) => place.title).join(' · ')}</td>
            <td>{group.places.map((place) => <Link key={place.id} className="admin-btn admin-btn-sm" to={`/admin/places/${place.id}`}>#{place.id}</Link>)}</td>
          </tr>
        ))}</tbody>
      </table>}
      {duplicateTotal > duplicateGroups.length && <p className="admin-muted">Показаны первые {duplicateGroups.length} из {duplicateTotal}. Уточните город, чтобы разобрать очередь.</p>}
    </section>}
    <section className="admin-help-panel"><strong>Следующий этап</strong><ul>{todo.map((text) => <li key={text}>{text}</li>)}</ul></section>
  </div>
}