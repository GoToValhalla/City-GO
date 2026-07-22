import { Link } from 'react-router-dom'
import type { AdminCityWorkspaceResponse } from './adminTypes'
import { humanizeCode, readinessStatusText } from './adminHumanText'
import { AdminPublicationDiagnostics } from './AdminPublicationDiagnostics'
import { WORKSPACE_TABS } from './adminWorkspaceTabs'

type Props = { data: AdminCityWorkspaceResponse; tab: string; busy: string | null; onImport: (action: string) => void; onPublish: () => void; onUnpublish: () => void }
const links = (slug: string, tab: string): Array<[string, string]> => ({ places: [['Открыть каталог города', `/admin/places?city=${slug}`]], quality: [['Открыть выборки качества', `/admin/quality?city_slug=${slug}`]], verification: [['Открыть очередь проверки', `/admin/verification?city=${slug}`]], photos: [['Открыть очередь фото', `/admin/photos?city=${slug}`]], enrichment: [['Открыть обогащение', `/admin/enrichment?city=${slug}`]], routes: [['Готовность маршрутов', `/admin/routes/eligibility?city_slug=${slug}`], ['Проверить сборку', `/admin/routes/dry-run?city=${slug}`]], history: [['Открыть журнал', `/admin/audit?city_slug=${slug}`]] }[tab] ?? []) as Array<[string, string]>
const metricUrl = (slug: string, key: string) => {
  const places = `/admin/places?city=${slug}`
  const urls: Record<string, string> = { readiness: `/admin/quality?city_slug=${slug}`, places, critical: `${places}&preset=problematic`, active_operations: `/admin/imports?city=${slug}`, published: `/admin/routes/data-quality?city=${slug}&status=published`, total: `/admin/routes/data-quality?city=${slug}`, eligible_places: `${places}&routes=true`, no_photo: `${places}&photo=false`, no_address: `${places}&address=false`, no_description: `${places}&description=false`, no_hours: `${places}&hours=false`, low_quality: `${places}&quality=low`, route_ineligible: `${places}&routes=false`, possible_duplicates: `/admin/quality?city_slug=${slug}&issue_type=possible_duplicate`, verification: `/admin/verification?city=${slug}`, photos: `/admin/photos?city=${slug}` }
  return urls[key] ?? places
}

export const AdminCityWorkspaceTabs = ({ data, tab, busy, onImport, onPublish, onUnpublish }: Props) => {
  const ops = data.operations ?? { quality: {}, queues: { verification: 0, photos: 0 }, routes: { published: 0, total: 0, eligible_places: 0 }, critical_issues: 0, active_operations: 0, recent_errors: [], recent_audit: [] }
  if (tab === 'overview') return <Overview data={data} />
  if (tab === 'import') return <ImportPanel data={data} busy={busy} onImport={onImport} />
  if (tab === 'publication') return <Publication data={data} busy={busy} onPublish={onPublish} onUnpublish={onUnpublish} />
  return <section className="admin-detail-panel"><h3>{WORKSPACE_TABS.find(([key]) => key === tab)?.[1] ?? 'Раздел'}</h3>{tab === 'quality' && <><p className="admin-muted">Это живые счётчики по карточкам города. “Не подходят для маршрутов” не всегда ошибка: для аптек, банков, клиник и сервисов это нормальное исключение из туристических маршрутов.</p><MetricRows slug={data.city.slug} values={ops.quality} showHints /></>}{tab === 'verification' && <MetricRows slug={data.city.slug} values={{ verification: ops.queues.verification }} />}{tab === 'photos' && <MetricRows slug={data.city.slug} values={{ photos: ops.queues.photos }} />}{tab === 'routes' && <MetricRows slug={data.city.slug} values={ops.routes} />}{tab === 'history' && (ops.recent_audit.length ? ops.recent_audit.map((row) => <Link className="admin-action-card" to={`/admin/audit?city_slug=${data.city.slug}&action=${encodeURIComponent(row.action)}`} key={row.id}>{row.actor}: {humanizeCode(row.action)} →</Link>) : <p>Событий нет.</p>)}{tab === 'enrichment' && <p>История запусков, шаги и field-level очередь доступны по постоянным ссылкам.</p>}<div className="admin-actions-cell">{links(data.city.slug, tab).map(([label, to]) => <Link className="admin-btn" key={to} to={to}>{label}</Link>)}</div></section>
}

const METRIC_LABELS: Record<string, string> = { readiness: 'Готовность', places: 'Места', critical: 'Критические проблемы', active_operations: 'Активные операции', published: 'Опубликованные маршруты', total: 'Всего', eligible_places: 'Места для маршрутов', no_photo: 'Без фото', no_address: 'Без адреса', no_description: 'Без описания', no_hours: 'Без часов работы', low_quality: 'Низкое качество', route_ineligible: 'Не подходят для маршрутов', possible_duplicates: 'Возможные дубли', verification: 'Открытые проверки', photos: 'Фото на проверке' }
const METRIC_HINTS: Record<string, string> = { no_photo: 'Нет основного фото. Сначала нужны реальные фото или кандидаты на проверку.', no_address: 'Адрес пустой. Координаты могут быть, но карточка неполная.', no_description: 'Нет короткого описания для карточки места.', no_hours: 'Нет часов работы. Для парков и улиц это может быть нормально, для ТЦ и музеев — проблема.', low_quality: 'Низкий внутренний quality score: карточку лучше проверить вручную.', route_ineligible: 'Уже исключены из маршрутов. Для сервисных категорий это ожидаемо.', possible_duplicates: 'Похожие места рядом с одинаковым названием. Нужна ручная проверка, merge или отклонение дубля.' }
const MetricRows = ({ values, slug, showHints = false }: { values: Record<string, number>; slug: string; showHints?: boolean }) => <div className="admin-metrics-grid">{Object.entries(values).map(([key, value]) => <Link className="admin-metric-card" to={metricUrl(slug, key)} key={key}><div className="admin-metric-value">{value}</div><div className="admin-metric-label">{METRIC_LABELS[key] ?? humanizeCode(key)}</div>{showHints && METRIC_HINTS[key] && <span className="admin-muted">{METRIC_HINTS[key]}</span>}<span className="admin-muted">Открыть набор →</span></Link>)}</div>
const Overview = ({ data }: { data: AdminCityWorkspaceResponse }) => {
  const ops = data.operations
  const blockerLinks = Object.fromEntries(
    Object.keys(data.readiness.blockers ?? {}).map((key) => [key, metricUrl(data.city.slug, key)]),
  )
  return (
    <>
      <MetricRows slug={data.city.slug} values={{ readiness: data.readiness.readiness_score, places: data.city.places_total ?? 0, critical: ops?.critical_issues ?? 0, active_operations: ops?.active_operations ?? 0 }} />
      <AdminPublicationDiagnostics
        title="Готовность города"
        readinessStatus={data.readiness.status}
        readinessScore={data.readiness.readiness_score}
        primaryBlocker={data.readiness.primary_blocker}
        blockers={data.readiness.blockers}
        blockerLinks={blockerLinks}
        snapshotWarning={data.import_job.snapshot_warning}
        snapshotFreshnessLabel={data.import_job.updated_at ? `обновлён ${new Date(data.import_job.updated_at).toLocaleString('ru-RU')}` : null}
        snapshotVersionLabel={null}
      />
      <section className="admin-detail-panel"><h3>Последние ошибки</h3>{ops?.recent_errors.length ? ops.recent_errors.map((row) => <Link className="admin-action-card" to={`/admin/system-logs?city_slug=${data.city.slug}&module=${encodeURIComponent(row.module)}&q=${encodeURIComponent(row.message)}`} key={row.id}>{row.module}: {row.message} →</Link>) : <p>Новых ошибок нет.</p>}</section>
    </>
  )
}
const ImportPanel = ({ data, busy, onImport }: { data: AdminCityWorkspaceResponse; busy: string | null; onImport: (action: string) => void }) => <section className="admin-detail-panel"><h3>Импорт</h3><p><Link to={`/admin/imports?city=${data.city.slug}&job=${data.import_job.job_id ?? ''}`}>{data.import_job.current_step_label} · {data.import_job.processed_items ?? 0}/{data.import_job.total_items ?? 0} →</Link></p><div className="admin-actions-cell"><Link className="admin-btn" to={`/admin/imports?city=${data.city.slug}`}>История запусков</Link>{data.import_job.can_run && <button className="admin-btn" disabled={!!busy} onClick={() => onImport('run')}>Запустить</button>}{data.import_job.can_retry && <button className="admin-btn" disabled={!!busy} onClick={() => onImport('retry')}>Повторить</button>}{data.import_job.can_cancel && <button className="admin-btn admin-btn-danger" disabled={!!busy} onClick={() => onImport('cancel')}>Отменить</button>}</div></section>
const Publication = ({ data, busy, onPublish, onUnpublish }: { data: AdminCityWorkspaceResponse; busy: string | null; onPublish: () => void; onUnpublish: () => void }) => {
  const blockerLinks = Object.fromEntries(
    Object.keys(data.readiness.blockers ?? {}).map((key) => [key, metricUrl(data.city.slug, key)]),
  )
  const statusDetail = data.readiness.primary_blocker
    ? undefined
    : readinessStatusText(data.readiness.status)
  return (
    <section className="admin-detail-panel">
      <h3>Публикация</h3>
      <AdminPublicationDiagnostics
        title="Диагностика перед публикацией"
        readinessStatus={data.readiness.status}
        readinessScore={data.readiness.readiness_score}
        primaryBlocker={data.readiness.primary_blocker}
        blockers={data.readiness.blockers}
        blockerLinks={blockerLinks}
        reviewBlockers={statusDetail && data.readiness.status !== 'ready' ? [statusDetail] : []}
        snapshotWarning={data.import_job.snapshot_warning}
        snapshotFreshnessLabel={data.import_job.finished_at ? `job завершён ${new Date(data.import_job.finished_at).toLocaleString('ru-RU')}` : data.import_job.current_step_label ?? null}
        snapshotVersionLabel={null}
      />
      <Link to={`/admin/places?city=${data.city.slug}&preset=problematic`}>Критических проблем: {data.operations?.critical_issues ?? 0} →</Link>
      <div className="admin-actions-cell">{data.city.can_publish && <button className="admin-btn admin-btn-primary" disabled={!!busy} onClick={onPublish}>Опубликовать</button>}{data.city.can_unpublish && <button className="admin-btn admin-btn-danger" disabled={!!busy} onClick={onUnpublish}>Снять с публикации</button>}</div>
    </section>
  )
}
