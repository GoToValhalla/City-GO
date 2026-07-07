import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import type { AdminImportCoverage, AdminImportChangeSummary, AdminImportJob, AdminImportJobsResponse } from './adminTypes'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

const STATUS_LABELS: Record<string, string> = {
  success: 'Завершён',
  success_with_warnings: 'Завершён с предупреждениями',
  partial_success: 'Частично завершён',
  imported: 'Завершён',
  queued: 'В очереди',
  importing: 'В очереди',
  failed: 'Ошибка',
  import_failed: 'Ошибка',
  running: 'Выполняется',
  review_required: 'На проверке',
  cancelled: 'Отменён',
  published: 'Опубликован',
  stalled: 'Завис',
  snapshot_refresh: 'Обновляем snapshot',
  snapshot_ready: 'Snapshot готов',
}

type AdminActionResponse = { message?: string }
type QueueRecoveryResponse = { marked: number; job_ids: number[]; queue: ImportQueueSummary }
type QueueRunOnceResponse = { scheduled: boolean; limit: number; queue: ImportQueueSummary }
type ImportQueueSummary = {
  total: number
  active_total?: number
  queued: number
  running: number
  stalled_running: number
  oldest_queued_seconds?: number | null
  longest_running_seconds?: number | null
  running_job_ids?: number[]
  stale_job_ids?: number[]
  next_job_ids?: number[]
  by_status?: Record<string, number>
  by_source?: Record<string, number>
}
type AnyDict = Record<string, unknown>

const asDict = (value: unknown): AnyDict => value && typeof value === 'object' && !Array.isArray(value) ? value as AnyDict : {}
const detailsOf = (job: AdminImportJob) => asDict(job.step_details)
const nested = (job: AdminImportJob, key: string) => asDict(detailsOf(job)[key])
const coverageOf = (job: AdminImportJob): AdminImportCoverage => job.data_coverage ?? nested(job, 'data_coverage') as AdminImportCoverage
const changesOf = (job: AdminImportJob): AdminImportChangeSummary => job.change_summary ?? nested(job, 'change_summary') as AdminImportChangeSummary
const text = (value: unknown, fallback = '—') => value === null || value === undefined || value === '' ? fallback : String(value)
const num = (value: unknown) => typeof value === 'number' ? value : Number(value ?? 0) || 0
const isRunningLike = (job: AdminImportJob) => ['queued', 'running'].includes(job.status)
const isSnapshotJob = (job: AdminImportJob) => job.source === 'admin_snapshot_refresh'
const isAddressJob = (job: AdminImportJob) => job.source === 'admin_address_enrichment'
const isPhotoJob = (job: AdminImportJob) => job.source === 'admin_photo_enrichment'
const isFullImportJob = (job: AdminImportJob) => ['admin_city_import', 'admin_city_enrichment'].includes(job.source)
const changesUrl = (job: AdminImportJob) => `/admin/imports/${job.city_slug}/jobs/${job.job_id ?? 'current'}/changes?city_id=${job.city_id}`
const logsUrl = (job: AdminImportJob) => job.logs_url ?? `/admin/system-logs?city_slug=${job.city_slug}&request_id=${job.job_id ?? ''}`
const sourceLabel = (source: string) => ({ admin_snapshot_refresh: 'snapshot', admin_address_enrichment: 'адреса', admin_photo_enrichment: 'фото', admin_city_import: 'полный импорт', admin_city_enrichment: 'обогащение' }[source] ?? source)
const statusText = (job: AdminImportJob) => jobStatusText(job)
const secondsText = (value?: number | null) => value == null ? '—' : value >= 3600 ? `${Math.floor(value / 3600)} ч ${Math.floor((value % 3600) / 60)} мин` : `${Math.floor(value / 60)} мин`
const formatDateTime = (value: unknown) => { if (!value) return null; const date = new Date(String(value)); return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) }
const snapshotAt = (job: AdminImportJob) => formatDateTime(detailsOf(job)['snapshot_at']) ?? 'snapshot не создан'
const isJobFailed = (job: AdminImportJob) => Boolean(job.job_execution_failed || job.is_stalled || job.status.includes('fail') || job.status === 'stalled' || job.import_error_summary)
const isDestinationPublished = (job: AdminImportJob) => job.destination_publication_status === 'published' || (job.launch_status === 'published' && job.is_city_active)
const jobStatusText = (job: AdminImportJob) => {
  if (isJobFailed(job)) return STATUS_LABELS[job.job_execution_status ?? job.status] ?? job.current_step_label ?? job.status
  return job.current_step_label ?? STATUS_LABELS[job.status] ?? job.status
}
const progressPct = (job: AdminImportJob) => (job.total_items ?? 0) > 0 ? Math.min(100, Math.round(((job.processed_items ?? 0) / (job.total_items ?? 1)) * 100)) : null
const progressInfo = (job: AdminImportJob) => {
  if (isJobFailed(job)) return { value: 'ошибка', label: 'импорт' }
  const pct = progressPct(job)
  if (isSnapshotJob(job)) return { value: isRunningLike(job) ? 'в работе' : detailsOf(job)['snapshot_at'] ? 'готов' : 'нет', label: 'snapshot' }
  if (isAddressJob(job)) return { value: isRunningLike(job) ? 'в работе' : 'готово', label: 'адреса' }
  if (isPhotoJob(job)) return { value: isRunningLike(job) ? 'в работе' : 'готово', label: 'фото' }
  return { value: pct !== null ? `${pct}%` : jobStatusText(job), label: pct !== null ? 'прогресс' : 'статус' }
}
const badgeTone = (job: AdminImportJob) => isJobFailed(job) ? 'hidden' : isRunningLike(job) ? 'needs_review' : 'draft'
const isBlockingImportError = (job: AdminImportJob) => Boolean(job.import_error_summary?.error_message || (job.last_error && isJobFailed(job)))

const ImportStatusBadges = ({ job }: { job: AdminImportJob }) => (
  <div className="admin-action-row">
    <span className={`admin-badge pub-${badgeTone(job)}`} data-testid="import-job-status-badge">{jobStatusText(job)}</span>
    {isDestinationPublished(job) ? <span className="admin-badge pub-published" data-testid="destination-publication-badge">Направление опубликовано</span> : null}
  </div>
)
const scrollToDetail = () => window.setTimeout(() => document.getElementById('admin-import-detail')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0)

const CoverageSummary = ({ job }: { job: AdminImportJob }) => {
  const coverage = coverageOf(job)
  return <><div className="admin-muted">адреса: {text(coverage.address_coverage_pct)}%</div><div className="admin-muted">фото: {text(coverage.photo_coverage_pct)}%</div><div className="admin-muted">описания: {text(coverage.description_coverage_pct)}%</div></>
}

const ImportActionButtons = ({ job, busy, onAction, onSelect, showDataActions = true }: { job: AdminImportJob, busy: number | null, onAction: (job: AdminImportJob, action: string, label: string) => void, onSelect: (job: AdminImportJob) => void, showDataActions?: boolean }) => {
  const active = isRunningLike(job)
  const disabled = busy === job.city_id || active
  return <div className="admin-actions-cell"><Link className="admin-btn admin-btn-sm" to={changesUrl(job)}>Изменения</Link><button type="button" className="admin-btn admin-btn-sm" onClick={() => onSelect(job)}>Детали</button><Link className="admin-btn admin-btn-sm" to={logsUrl(job)}>Логи</Link>{active && <span className="admin-muted">Действия заблокированы: pipeline выполняется</span>}{showDataActions && <><button type="button" className="admin-btn admin-btn-sm" disabled={disabled} onClick={() => onAction(job, 'snapshot/refresh', 'Обновить snapshot')}>Обновить snapshot</button><button type="button" className="admin-btn admin-btn-sm" disabled={disabled} onClick={() => onAction(job, 'enrich-addresses', 'Добрать адреса')}>Добрать адреса</button><button type="button" className="admin-btn admin-btn-sm" disabled={disabled} onClick={() => onAction(job, 'enrich-photos', 'Добрать фото')}>Добрать фото</button></>}{job.can_run && <button type="button" className="admin-btn admin-btn-sm" disabled={busy === job.city_id} onClick={() => onAction(job, 'run', 'Запустить сбор')}>Запустить сбор</button>}{job.can_retry && <button type="button" className="admin-btn admin-btn-sm" disabled={busy === job.city_id || active} onClick={() => onAction(job, 'retry', 'Повторить сбор')}>Повторить сбор</button>}{job.can_cancel && <button type="button" className="admin-btn admin-btn-sm" disabled={busy === job.city_id} onClick={() => onAction(job, 'cancel', 'Отменить')}>Отменить</button>}{job.can_publish && <button type="button" className="admin-btn admin-btn-sm admin-btn-primary" disabled={busy === job.city_id || active} onClick={() => onAction(job, 'publish', 'Опубликовать город')}>Опубликовать</button>}</div>
}

const WorkerQueuePanel = ({ queue, loading, error, runLoading, runNotice, runError, onRefresh, onRunOnce, onMarkStalled }: { queue: ImportQueueSummary | null, loading: boolean, error: string | null, runLoading: boolean, runNotice: string | null, runError: string | null, onRefresh: () => void, onRunOnce: () => void, onMarkStalled: () => void }) => {
  const hasWork = Boolean(queue && (queue.queued > 0 || queue.running > 0 || queue.stalled_running > 0))
  const running = queue?.running ?? 0
  const runDisabled = runLoading || running > 0
  const sources = Object.entries(queue?.by_source ?? {}).filter(([, value]) => value > 0)
  return <section className={hasWork ? 'admin-warning-panel' : 'admin-help-panel'}><div className="admin-help-title">Очередь import-worker</div>{error ? <p className="admin-error-text">Очередь недоступна: {error}</p> : loading && !queue ? <p className="admin-muted">Загрузка очереди…</p> : <><p>В очереди: <strong>{queue?.queued ?? 0}</strong> · выполняется: <strong>{running}</strong> · зависших: <strong>{queue?.stalled_running ?? 0}</strong></p>{queue?.longest_running_seconds != null && queue.longest_running_seconds > 0 && <p className="admin-muted">Самая долгая running-задача: {secondsText(queue.longest_running_seconds)}</p>}{sources.length > 0 && <p className="admin-muted">Активные типы: {sources.map(([key, value]) => `${sourceLabel(key)}: ${value}`).join(' · ')}</p>}{queue?.stale_job_ids?.length ? <p className="admin-error-text">Зависшие job id: {queue.stale_job_ids.join(', ')}</p> : null}{queue?.next_job_ids?.length ? <p className="admin-muted">Следующие job id: {queue.next_job_ids.join(', ')}</p> : null}{!hasWork && <p className="admin-muted">Фоновых задач сейчас нет.</p>}</>}{loading && queue ? <p className="admin-muted">Обновляем очередь…</p> : null}{runNotice ? <p className="admin-success-text">{runNotice}</p> : null}{runError ? <p className="admin-error-text">Worker не запущен: {runError}</p> : null}<button type="button" className="admin-btn admin-btn-sm admin-btn-primary" aria-busy={loading} onClick={() => onRefresh()}>Обновить очередь</button><button type="button" className="admin-btn admin-btn-sm" aria-busy={runLoading} disabled={runDisabled} onClick={() => onRunOnce()}>{runLoading ? 'Запускаем worker…' : 'Запустить worker один раз'}</button>{running > 0 ? <span className="admin-muted">Worker уже выполняет задачу. Повторный запуск заблокирован.</span> : null}{(queue?.stalled_running ?? 0) > 0 && <button type="button" className="admin-btn admin-btn-danger admin-btn-sm" onClick={onMarkStalled}>Пометить зависшие</button>}</section>
}

export const AdminImportJobsPage = () => {
  const [params, setParams] = useSearchParams()
  const cityFilter = params.get('city') ?? ''
  const jobFilter = params.get('job') ?? ''
  const [items, setItems] = useState<AdminImportJob[]>([])
  const [selected, setSelected] = useState<AdminImportJob | null>(null)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState<number | null>(null)
  const [allBusy, setAllBusy] = useState(false)
  const [queue, setQueue] = useState<ImportQueueSummary | null>(null)
  const [queueLoading, setQueueLoading] = useState(false)
  const [queueError, setQueueError] = useState<string | null>(null)
  const [workerRunLoading, setWorkerRunLoading] = useState(false)
  const [workerRunNotice, setWorkerRunNotice] = useState<string | null>(null)
  const [workerRunError, setWorkerRunError] = useState<string | null>(null)

  const loadQueue = useCallback(() => { setQueueLoading(true); setQueueError(null); adminGet<ImportQueueSummary>('/admin/import-queue', { cache: false, timeoutMs: 8000 }).then(setQueue).catch((e: Error) => setQueueError(e.message)).finally(() => setQueueLoading(false)) }, [])
  const reload = useCallback((silent = false) => { if (!silent) setLoading(true); adminGet<AdminImportJobsResponse>('/admin/import-jobs?limit=50', { cache: false }).then((r) => { setItems(r.items); setTotal(r.total) }).catch((e: Error) => setError(e.message)).finally(() => { if (!silent) setLoading(false) }) }, [])
  const refreshAll = useCallback((silent = false) => { reload(silent); loadQueue() }, [reload, loadQueue])
  const loadDetail = useCallback((cityId: number) => { setError(null); adminGet<AdminImportJob>(`/admin/import-jobs/${cityId}`, { cache: false }).then((detail) => { setSelected(detail); scrollToDetail() }).catch((e: Error) => setError(`Детали не открылись: ${e.message}`)) }, [])
  useEffect(() => { refreshAll() }, [refreshAll])
  useEffect(() => { const match = jobFilter ? items.find((item) => String(item.job_id ?? '') === jobFilter) : cityFilter ? items.find((item) => item.city_slug === cityFilter) : undefined; if (match) loadDetail(match.city_id) }, [items, jobFilter, cityFilter, loadDetail])
  const hasActiveJobs = useMemo(() => items.some(isRunningLike), [items])
  useEffect(() => { if (!hasActiveJobs) return undefined; const intervalId = window.setInterval(() => refreshAll(true), 7000); return () => window.clearInterval(intervalId) }, [hasActiveJobs, refreshAll])
  const visibleItems = useMemo(() => cityFilter ? items.filter((item) => item.city_slug === cityFilter) : items, [items, cityFilter])
  const selectDetail = (job: AdminImportJob) => { const next = new URLSearchParams(params); next.set('city', job.city_slug); if (job.job_id != null) next.set('job', String(job.job_id)); else next.set('detail', String(job.city_id)); setParams(next); setSelected(job); scrollToDetail(); loadDetail(job.city_id) }
  const closeDetail = () => { const next = new URLSearchParams(params); next.delete('job'); next.delete('detail'); setParams(next); setSelected(null) }
  const clearFilter = () => { const next = new URLSearchParams(params); next.delete('city'); next.delete('job'); next.delete('detail'); setParams(next); setSelected(null) }
  const runAction = async (job: AdminImportJob, action: string, label: string) => { if (!window.confirm(`${label}: ${job.city_name}?`)) return; setBusy(job.city_id); setError(null); setNotice(null); try { const response = await adminPost<AdminActionResponse>(`/admin/import-jobs/${job.city_id}/${action}`, action === 'publish' ? { reason: 'admin_import_publish' } : {}); setNotice(response.message ?? 'Действие поставлено в очередь.'); refreshAll(true); loadDetail(job.city_id) } catch (e) { setError(e instanceof Error ? e.message : 'Ошибка') } finally { setBusy(null) } }
  const runAll = async () => { if (!window.confirm('Собрать и обогатить все города? Для каждого города будет поставлена отдельная фоновая задача.')) return; setAllBusy(true); setError(null); try { const response = await adminPost<AdminActionResponse>('/admin/import-jobs/enrich-all', {}); setNotice(response.message ?? 'Полный pipeline поставлен в очередь.'); refreshAll(true) } catch (e) { setError(e instanceof Error ? e.message : 'Ошибка') } finally { setAllBusy(false) } }
  const runWorkerOnce = async () => { setWorkerRunLoading(true); setWorkerRunError(null); setWorkerRunNotice(null); try { const response = await adminPost<QueueRunOnceResponse>('/admin/import-queue/run-once', {}); setQueue(response.queue); setWorkerRunNotice(response.scheduled ? `Worker запущен один раз. Лимит: ${response.limit}.` : 'Worker не был запущен.'); loadQueue(); reload(true) } catch (e) { setWorkerRunError(e instanceof Error ? e.message : 'Ошибка') } finally { setWorkerRunLoading(false) } }
  const markStalled = async () => { if (!window.confirm('Пометить зависшие running-задачи как stalled? После этого их можно будет запускать заново.')) return; setError(null); setNotice(null); try { const response = await adminPost<QueueRecoveryResponse>('/admin/import-queue/mark-stalled', {}); setNotice(`Зависшие задачи помечены: ${response.marked}.`); setQueue(response.queue); reload(true) } catch (e) { setError(e instanceof Error ? e.message : 'Ошибка') } }

  return <div><h2 className="admin-page-title">Сбор и обогащение ({cityFilter ? visibleItems.length : total})</h2><p className="admin-page-subtitle">Список читает только лёгкие counters/snapshot. Тяжёлые расчёты запускаются POST-действиями и import-worker.</p><section className="admin-help-panel"><div className="admin-help-title">Полный запуск для всех городов</div><p className="admin-muted">HTTP-запуск только ставит задачу в очередь. Выполнение делает import-worker, состояние очереди обновляется кнопкой ниже.</p><button type="button" className="admin-btn" disabled={allBusy || items.length === 0} onClick={() => void runAll()}>{allBusy ? 'Ставим задачи…' : 'Собрать и обогатить все города'}</button>{cityFilter && <button type="button" className="admin-btn" onClick={clearFilter}>Показать все города</button>}</section><WorkerQueuePanel queue={queue} loading={queueLoading} error={queueError} runLoading={workerRunLoading} runNotice={workerRunNotice} runError={workerRunError} onRefresh={loadQueue} onRunOnce={() => void runWorkerOnce()} onMarkStalled={() => void markStalled()} />{notice && <p className="admin-success-text">{notice}</p>}{error && <AdminError message={error} />}{loading ? <AdminLoading /> : visibleItems.length === 0 ? <AdminEmpty message="Задач по выбранному фильтру нет" /> : <><ImportJobsCards items={visibleItems} busy={busy} onAction={runAction} onSelect={selectDetail} />{selected && <ImportJobDetail selected={selected} busy={busy} onAction={runAction} onClose={closeDetail} />}<ImportJobsTable items={visibleItems} busy={busy} onAction={runAction} onSelect={selectDetail} /></>}</div>
}

const ImportJobsCards = ({ items, busy, onAction, onSelect }: { items: AdminImportJob[], busy: number | null, onAction: (job: AdminImportJob, action: string, label: string) => void, onSelect: (job: AdminImportJob) => void }) => <div className="admin-import-card-list">{items.map((job) => { const progress = progressInfo(job); return <article className="admin-import-card" key={job.id}><div className="admin-import-card-head"><div><Link to={`/admin/cities/${job.city_slug}?tab=import`}>{job.city_name}</Link><div className="admin-muted">{job.city_slug} · запуск #{job.job_id ?? 'текущий'} · {sourceLabel(job.source)}</div></div><ImportStatusBadges job={job} /></div><div className="admin-import-card-grid"><div><strong>{job.places_total}</strong><span>мест</span></div><div><strong>{job.places_published}</strong><span>на сайте</span></div><div><strong>{progress.value}</strong><span>{progress.label}</span></div></div><CoverageSummary job={job} /><div className="admin-muted">snapshot: {snapshotAt(job)}</div><ImportActionButtons job={job} busy={busy} onAction={onAction} onSelect={onSelect} /></article> })}</div>
const ImportJobsTable = ({ items, busy, onAction, onSelect }: { items: AdminImportJob[], busy: number | null, onAction: (job: AdminImportJob, action: string, label: string) => void, onSelect: (job: AdminImportJob) => void }) => <div className="admin-table-wrap admin-import-table"><table className="admin-table"><thead><tr><th>Город</th><th>Запуск</th><th>Шаг</th><th>Статус</th><th>Покрытие</th><th>Действия</th></tr></thead><tbody>{items.map((job) => { const progress = progressInfo(job); const contract = nested(job, 'admin_pipeline_contract'); return <tr key={job.id} className={job.is_stalled ? 'admin-row-warning' : ''}><td><Link to={`/admin/cities/${job.city_slug}?tab=import`}>{job.city_name}</Link><div className="admin-muted">{job.city_slug}</div><div className="admin-muted">{text(contract['label'], job.pipeline_mode_label ?? 'OSM + foundation')}</div></td><td><button className="admin-btn admin-btn-sm" onClick={() => onSelect(job)}>#{job.job_id ?? 'текущий'} →</button><div className="admin-muted">{formatDateTime(job.created_at) ?? ''}</div></td><td><span className={`admin-badge pub-${badgeTone(job)}`}>{statusText(job)}</span>{isRunningLike(job) && <div className="admin-muted">pipeline выполняется</div>}<div className="admin-muted">{snapshotAt(job)}</div></td><td><strong>{progress.value}</strong><div className="admin-muted">{progress.label}</div>{isFullImportJob(job) && <div className="admin-muted">найдено: {job.places_found ?? 0}, сохранено: {job.places_saved ?? 0}</div>}</td><td><Link to={`/admin/places?city=${job.city_slug}`}>{job.places_total}</Link><CoverageSummary job={job} /></td><td><ImportActionButtons job={job} busy={busy} onAction={onAction} onSelect={onSelect} /></td></tr> })}</tbody></table></div>
const ImportJobRuntime = ({ job }: { job: AdminImportJob }) => { const details = detailsOf(job); const photoValue = details['photo_enrichment'] ?? details['latest_photo_enrichment']; const addressValue = details['address_enrichment'] ?? details['latest_address_enrichment']; const hasPhotoValue = photoValue !== undefined && photoValue !== null; const hasAddressValue = addressValue !== undefined && addressValue !== null; if (hasPhotoValue || hasAddressValue || isPhotoJob(job) || isAddressJob(job)) return <>{(hasPhotoValue || isPhotoJob(job)) && <details open><summary>Результат добора фото</summary>{hasPhotoValue ? <pre>{JSON.stringify(photoValue, null, 2)}</pre> : <p className="admin-muted">Подробный результат ещё не записан.</p>}</details>}{(hasAddressValue || isAddressJob(job)) && <details open><summary>Результат добора адресов</summary>{hasAddressValue ? <pre>{JSON.stringify(addressValue, null, 2)}</pre> : <p className="admin-muted">Подробный результат ещё не записан.</p>}</details>}{isSnapshotJob(job) && <p className="admin-muted">Snapshot-операция обновляет только coverage и не использует processed/total.</p>}</>; if (isSnapshotJob(job)) return <p className="admin-muted">Snapshot-операция обновляет только coverage и не использует processed/total.</p>; return <><p>Обработано: {job.processed_items ?? 0}/{job.total_items ?? 0} · успешно: {job.successful_items ?? 0} · ошибок: {job.failed_items ?? 0}</p><p>Найдено: {job.places_found ?? 0} · сохранено: {job.places_saved ?? 0}</p></> }
const ImportExecutionSummary = ({ job }: { job: AdminImportJob }) => {
  const summary = job.import_execution_summary ?? {}
  return <section className="admin-help-panel" data-testid="import-execution-summary"><div className="admin-help-title">Сбор и классификация</div><p>Собрано: <strong>{text(summary.raw_collected)}</strong> · сохранено: <strong>{text(summary.raw_saved)}</strong> · на сайте: <strong>{text(summary.published)}</strong></p><p>Контуры: <strong>{text(summary.scopes_succeeded)}</strong> / <strong>{text(summary.scopes_total)}</strong>{summary.scopes_failed != null ? <> · ошибок контуров: <strong>{text(summary.scopes_failed)}</strong></> : null}</p><p>На проверку: <strong>{text(summary.needs_review)}</strong> · скрыто: <strong>{text(summary.hidden)}</strong> · отклонено: <strong>{text(summary.rejected)}</strong></p></section>
}
const ImportJobDetail = ({ selected, busy, onAction, onClose }: { selected: AdminImportJob, busy: number | null, onAction: (job: AdminImportJob, action: string, label: string) => void, onClose: () => void }) => { const details = detailsOf(selected); const coverage = coverageOf(selected); const changes = changesOf(selected); const contract = nested(selected, 'admin_pipeline_contract'); const photoDiagnostics = asDict(selected.photo_diagnostics ?? details['photo_diagnostics']); const noPhotoCandidates = num(coverage.without_photo) > 0 && num(coverage.pending_photos) === 0; const errorSummary = selected.import_error_summary; return <div id="admin-import-detail" className="admin-detail-panel"><h3>{selected.city_name} · запуск #{selected.job_id ?? 'текущий'}</h3><ImportStatusBadges job={selected} /><p>Шаг импорта: <strong>{jobStatusText(selected)}</strong></p><p>Фоновая задача: <strong>{sourceLabel(selected.source)}</strong></p><p>Действие: <strong>{text(details['admin_action_hint'] ?? selected.action_hint)}</strong></p><p>Pipeline: <strong>{text(contract['label'], selected.pipeline_mode_label ?? 'OSM + foundation')}</strong></p><p>{selected.next_step}</p>{selected.snapshot_warning ? <p className="admin-state admin-state-warning" data-testid="snapshot-missing-warning">{selected.snapshot_warning.message}</p> : <p className="admin-muted">Snapshot: {snapshotAt(selected)}</p>}{errorSummary ? <section className="admin-state admin-state-error" data-testid="import-error-summary"><strong>Ошибка импорта</strong><p>Шаг: {text(errorSummary.failed_step)}</p><p>{text(errorSummary.error_message)}</p></section> : null}<div className="admin-metrics-grid"><div className="admin-metric-card"><div className="admin-metric-value">{selected.places_total}</div><div className="admin-metric-label">мест в городе</div></div><div className="admin-metric-card"><div className="admin-metric-value">{selected.places_published}</div><div className="admin-metric-label">на сайте</div></div><div className="admin-metric-card"><div className="admin-metric-value">{num(changes.total_changes)}</div><div className="admin-metric-label">изменений</div></div><div className="admin-metric-card"><div className="admin-metric-value">{selected.failed_items ?? 0}</div><div className="admin-metric-label">ошибок</div></div></div><section className="admin-help-panel"><div className="admin-help-title">Покрытие критичными данными</div><p>Адреса: <strong>{text(coverage.address_coverage_pct)}%</strong> · без адреса: {text(coverage.without_address)}</p><p>Фото: <strong>{text(coverage.photo_coverage_pct)}%</strong> · без фото: {text(coverage.without_photo)} · кандидатов на проверку: {text(coverage.pending_photos)}</p>{noPhotoCandidates ? <p className="admin-error-text" data-testid="photo-blocker-hint">{text(photoDiagnostics['admin_hint'], 'Фото остаются блокером: мест без фото много, кандидатов на проверку нет. Добор фото должен вернуть явный результат/provider warning.')}</p> : null}{noPhotoCandidates && photoDiagnostics['provider_status'] ? <p className="admin-muted" data-testid="photo-diagnostics-status">Диагностика фото: {text(photoDiagnostics['provider_status'])}{photoDiagnostics['zero_result_reason'] ? ` · ${text(photoDiagnostics['zero_result_reason'])}` : ''}</p> : null}<p>Описания: <strong>{text(coverage.description_coverage_pct)}%</strong> · без описания: {text(coverage.without_description)}</p><div className="admin-actions-cell"><button type="button" className="admin-btn admin-btn-sm" disabled={busy === selected.city_id || isRunningLike(selected)} onClick={() => onAction(selected, 'enrich-addresses', 'Добрать адреса')}>Добрать адреса</button><button type="button" className="admin-btn admin-btn-sm" disabled={busy === selected.city_id || isRunningLike(selected)} onClick={() => onAction(selected, 'enrich-photos', 'Добрать фото')}>Добрать фото</button><button type="button" className="admin-btn admin-btn-sm" disabled={busy === selected.city_id || isRunningLike(selected)} onClick={() => onAction(selected, 'snapshot/refresh', 'Обновить snapshot')}>Обновить snapshot</button></div></section><section className="admin-help-panel"><div className="admin-help-title">Отчёт изменений</div><p>Новые: <strong>{text(changes.created, '0')}</strong> · обновлённые: <strong>{text(changes.updated, '0')}</strong> · на проверку: <strong>{text(changes.needs_review, '0')}</strong> · скрытые: <strong>{text(changes.hidden, '0')}</strong> · отклонённые: <strong>{text(changes.rejected, '0')}</strong> · без изменений: <strong>{text(changes.unchanged, '0')}</strong></p></section><ImportExecutionSummary job={selected} /><ImportJobRuntime job={selected} />{isBlockingImportError(selected) && !errorSummary && <p className="admin-error-text">Ошибка: {selected.last_error}</p>}{selected.last_error && !isBlockingImportError(selected) && <details><summary>Старая сохранённая ошибка</summary><p className="admin-muted">Это ошибка прошлого шага. Текущий статус: {statusText(selected)}; failed_items={selected.failed_items ?? 0}.</p><pre>{selected.last_error}</pre></details>}{selected.step_details && <details><summary>Технические детали pipeline</summary><pre>{JSON.stringify(selected.step_details, null, 2)}</pre></details>}<div className="admin-actions-cell"><Link className="admin-btn admin-btn-sm" to={changesUrl(selected)}>Изменения</Link><Link className="admin-btn admin-btn-sm" to={logsUrl(selected)}>Логи</Link>{selected.can_retry && <button type="button" className="admin-btn admin-btn-sm" disabled={busy === selected.city_id || isRunningLike(selected)} onClick={() => onAction(selected, 'retry', 'Повторить сбор')}>Повторить сбор</button>}{selected.can_cancel && <button type="button" className="admin-btn admin-btn-sm" disabled={busy === selected.city_id} onClick={() => onAction(selected, 'cancel', 'Отменить')}>Отменить</button>}{selected.can_publish && <button type="button" className="admin-btn admin-btn-sm admin-btn-primary" disabled={busy === selected.city_id || isRunningLike(selected)} onClick={() => onAction(selected, 'publish', 'Опубликовать город')}>Опубликовать</button>}{selected.report_url && <Link className="admin-btn admin-btn-sm" to={selected.report_url}>Отчёт качества</Link>}<Link className="admin-btn admin-btn-sm" to={`/admin/places?city=${selected.city_slug}`}>Все места</Link><Link className="admin-btn admin-btn-sm" to={`/admin/places?city=${selected.city_slug}&verification=needs_recheck`}>Изменённые места</Link><Link className="admin-btn admin-btn-sm" to={`/admin/audit?entity_type=import_job&entity_id=${selected.job_id ?? ''}`}>Аудит запуска</Link><button type="button" className="admin-btn admin-btn-sm" onClick={onClose}>Закрыть</button></div></div> }
