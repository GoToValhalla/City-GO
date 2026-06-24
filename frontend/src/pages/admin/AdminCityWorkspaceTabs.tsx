import { Link } from 'react-router-dom'
import type { AdminCityWorkspaceResponse } from './adminTypes'
import { humanizeCode } from './adminHumanText'
import { WORKSPACE_TABS } from './adminWorkspaceTabs'

type Props = {
  data: AdminCityWorkspaceResponse
  tab: string
  busy: string | null
  onImport: (action: string) => void
  onPublish: () => void
  onUnpublish: () => void
}

const links = (slug: string, tab: string): Array<[string, string]> => ({
  places: [['Открыть каталог города', `/admin/places?city=${slug}`]],
  quality: [['Открыть выборки качества', `/admin/quality?city_slug=${slug}`]],
  verification: [['Открыть очередь проверки', `/admin/verification?city=${slug}`]],
  photos: [['Открыть очередь фото', `/admin/photos?city=${slug}`]],
  enrichment: [['Открыть обогащение', `/admin/enrichment?city=${slug}`]],
  routes: [['Готовность маршрутов', `/admin/routes/eligibility?city_slug=${slug}`], ['Проверить сборку', `/admin/routes/dry-run?city=${slug}`]],
  history: [['Открыть журнал', `/admin/audit?city_slug=${slug}`]],
}[tab] ?? []) as Array<[string, string]>

export const AdminCityWorkspaceTabs = ({ data, tab, busy, onImport, onPublish, onUnpublish }: Props) => {
  const ops = data.operations ?? {
    quality: {}, queues: { verification: 0, photos: 0 },
    routes: { published: 0, total: 0, eligible_places: 0 },
    critical_issues: 0, active_operations: 0, recent_errors: [], recent_audit: [],
  }
  if (tab === 'overview') return <Overview data={data} />
  if (tab === 'import') return <ImportPanel data={data} busy={busy} onImport={onImport} />
  if (tab === 'publication') return <Publication data={data} busy={busy} onPublish={onPublish} onUnpublish={onUnpublish} />
  return (
    <section className="admin-detail-panel">
      <h3>{WORKSPACE_TABS.find(([key]) => key === tab)?.[1] ?? 'Раздел'}</h3>
      {tab === 'quality' ? <MetricRows values={ops.quality} /> : null}
      {tab === 'verification' ? <p>Открытых проверок: <strong>{ops.queues.verification}</strong></p> : null}
      {tab === 'photos' ? <p>Фото на проверке: <strong>{ops.queues.photos}</strong></p> : null}
      {tab === 'routes' ? <MetricRows values={ops.routes} /> : null}
      {tab === 'history' ? ops.recent_audit.map((row) => <p key={row.id}>{row.actor}: {humanizeCode(row.action)}</p>) : null}
      {tab === 'enrichment' ? <p>История и field-level очередь доступны в разделе обогащения.</p> : null}
      <div className="admin-actions-cell">{links(data.city.slug, tab).map(([label, to]) => <Link className="admin-btn" key={to} to={to}>{label}</Link>)}</div>
    </section>
  )
}

const METRIC_LABELS: Record<string, string> = {
  readiness: 'Готовность', places: 'Места', critical: 'Критические проблемы',
  active_operations: 'Активные операции', published: 'Опубликованные маршруты',
  total: 'Всего', eligible_places: 'Места для маршрутов',
  no_photo: 'Без фото', no_address: 'Без адреса', no_description: 'Без описания',
  no_hours: 'Без часов работы', low_quality: 'Низкое качество', route_ineligible: 'Не подходят для маршрутов',
}
const MetricRows = ({ values }: { values: Record<string, number> }) => <div className="admin-metrics-grid">{Object.entries(values).map(([key, value]) => <div className="admin-metric-card" key={key}><div className="admin-metric-value">{value}</div><div className="admin-metric-label">{METRIC_LABELS[key] ?? humanizeCode(key)}</div></div>)}</div>
const Overview = ({ data }: { data: AdminCityWorkspaceResponse }) => {
  const ops = data.operations
  return <><MetricRows values={{ readiness: data.readiness.readiness_score, places: data.city.places_total ?? 0, critical: ops?.critical_issues ?? 0, active_operations: ops?.active_operations ?? 0 }} /><section className="admin-detail-panel"><h3>Последние ошибки</h3>{ops?.recent_errors.length ? ops.recent_errors.map((row) => <p key={row.id}>{row.module}: {row.message}</p>) : <p>Новых ошибок нет.</p>}</section></>
}
const ImportPanel = ({ data, busy, onImport }: { data: AdminCityWorkspaceResponse; busy: string | null; onImport: (action: string) => void }) => <section className="admin-detail-panel"><h3>Импорт</h3><p>{data.import_job.current_step_label} · {data.import_job.processed_items ?? 0}/{data.import_job.total_items ?? 0}</p><div className="admin-actions-cell">{data.import_job.can_run && <button className="admin-btn" disabled={!!busy} onClick={() => onImport('run')}>Запустить</button>}{data.import_job.can_retry && <button className="admin-btn" disabled={!!busy} onClick={() => onImport('retry')}>Повторить</button>}{data.import_job.can_cancel && <button className="admin-btn admin-btn-danger" disabled={!!busy} onClick={() => onImport('cancel')}>Отменить</button>}</div></section>
const Publication = ({ data, busy, onPublish, onUnpublish }: { data: AdminCityWorkspaceResponse; busy: string | null; onPublish: () => void; onUnpublish: () => void }) => <section className="admin-detail-panel"><h3>Публикация</h3><p>Критических проблем: {data.operations?.critical_issues ?? 0}</p><div className="admin-actions-cell">{data.city.can_publish && <button className="admin-btn admin-btn-primary" disabled={!!busy} onClick={onPublish}>Опубликовать</button>}{data.city.can_unpublish && <button className="admin-btn admin-btn-danger" disabled={!!busy} onClick={onUnpublish}>Снять с публикации</button>}</div></section>
