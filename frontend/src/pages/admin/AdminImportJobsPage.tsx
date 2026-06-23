import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import type { AdminImportJob, AdminImportJobsResponse } from './adminTypes'
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
}

type AdminActionResponse = {
  message?: string
}

const detailLine = (label: string, value: unknown) => value === null || value === undefined || value === '' ? null : <p>{label}: <strong>{String(value)}</strong></p>

export const AdminImportJobsPage = () => {
  const [items, setItems] = useState<AdminImportJob[]>([])
  const [selected, setSelected] = useState<AdminImportJob | null>(null)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState<number | null>(null)
  const [allBusy, setAllBusy] = useState(false)

  const reload = useCallback(() => {
    setLoading(true)
    adminGet<AdminImportJobsResponse>('/admin/import-jobs?limit=50')
      .then((r) => { setItems(r.items); setTotal(r.total) })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { reload() }, [reload])

  const loadDetail = (cityId: number) => {
    adminGet<AdminImportJob>(`/admin/import-jobs/${cityId}`)
      .then(setSelected)
      .catch((e: Error) => setError(e.message))
  }

  const runAction = async (cityId: number, path: string, label = 'Выполнить действие') => {
    if (!window.confirm(`${label}? Действие запустит фоновую операцию по выбранному городу.`)) return
    setBusy(cityId)
    setError(null)
    setNotice(null)
    try {
      const response = await adminPost<AdminActionResponse>(path, {})
      setNotice(response.message ?? 'Действие выполнено.')
      reload()
      loadDetail(cityId)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка')
    } finally { setBusy(null) }
  }

  const runAll = async () => {
    if (!window.confirm('Собрать и обогатить все города? Для каждого города будет поставлена отдельная фоновая задача. Автопубликации не будет.')) return
    setAllBusy(true)
    setError(null)
    setNotice(null)
    try {
      const response = await adminPost<{ message?: string }>('/admin/import-jobs/enrich-all', {})
      setNotice(response.message ?? 'Полный pipeline для городов поставлен в очередь.')
      reload()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка')
    } finally { setAllBusy(false) }
  }

  const progressPct = (j: AdminImportJob) => {
    const totalItems = j.total_items ?? 0
    const processed = j.processed_items ?? 0
    if (totalItems <= 0) return null
    return Math.min(100, Math.round((processed / totalItems) * 100))
  }

  return (
    <div>
      <h2 className="admin-page-title">Сбор и обогащение ({total})</h2>
      <p className="admin-page-subtitle">Процесс: досбор мест → дедупликация → адреса → фото → внешние источники → качество → проверка → публикация</p>
      <section className="admin-help-panel">
        <div className="admin-help-title">Полный запуск для всех городов</div>
        <p className="admin-bulk-hint">Система повторно проверит настроенные зоны OSM, сохранит новые места без дублей и затем заполнит доступные данные. Города не публикуются автоматически.</p>
        <button type="button" className="admin-btn" disabled={allBusy || items.length === 0} onClick={runAll}>
          {allBusy ? 'Ставим задачи…' : 'Собрать и обогатить все города'}
        </button>
      </section>
      {notice && <p className="admin-success-text">{notice}</p>}
      {error && <AdminError message={error} />}
      {loading ? <AdminLoading /> : items.length === 0 ? (
        <AdminEmpty message="Задач пока нет" />
      ) : (
        <div className="admin-table-wrap"><table className="admin-table">
          <thead><tr><th>Город</th><th>Шаг</th><th>Публикация</th><th>Прогресс</th><th>Мест</th><th>Действия</th></tr></thead>
          <tbody>
            {items.map((j) => {
              const pct = progressPct(j)
              const stalled = j.is_stalled
              return (
                <tr key={j.id} className={stalled ? 'admin-row-warning' : ''}>
                  <td>{j.city_name}<div className="admin-muted">{j.city_slug}</div></td>
                  <td>
                    <span className={`admin-badge pub-${j.status.includes('fail') ? 'hidden' : j.status === 'running' ? 'needs_review' : 'published'}`}>
                      {j.current_step_label ?? STATUS_LABELS[j.status] ?? j.status}
                    </span>
                    {stalled && <div className="admin-error-text">Возможно зависла</div>}
                  </td>
                  <td>{STATUS_LABELS[j.launch_status ?? ''] ?? j.launch_status ?? '—'}</td>
                  <td>{pct !== null ? `${pct}% (${j.processed_items ?? 0}/${j.total_items ?? 0})` : '—'}</td>
                  <td>{j.places_total}<div className="admin-muted">на сайте: {j.places_published}</div></td>
                  <td className="admin-actions-cell">
                    <button type="button" className="admin-btn admin-btn-sm" onClick={() => loadDetail(j.city_id)}>Детали</button>
                    {j.can_run && <button type="button" className="admin-btn admin-btn-sm" disabled={busy === j.city_id} onClick={() => runAction(j.city_id, `/admin/import-jobs/${j.city_id}/run`, 'Собрать и обогатить город')}>Собрать и обогатить</button>}
                    {j.can_retry && <button type="button" className="admin-btn admin-btn-sm admin-btn-muted" disabled={busy === j.city_id} onClick={() => runAction(j.city_id, `/admin/import-jobs/${j.city_id}/retry`, 'Повторить полный запуск')}>Повторить</button>}
                    {j.can_publish && <button type="button" className="admin-btn admin-btn-sm" disabled={busy === j.city_id} onClick={() => runAction(j.city_id, `/admin/import-jobs/${j.city_id}/publish`, 'Опубликовать город')}>Опубликовать</button>}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table></div>
      )}
      {selected && (
        <div className="admin-detail-panel">
          <h3>{selected.city_name}</h3>
          <p>Шаг: <strong>{selected.current_step_label ?? STATUS_LABELS[selected.status] ?? selected.status}</strong> · задача #{selected.job_id ?? '—'}</p>
          <p>Публикация: <strong>{STATUS_LABELS[selected.launch_status ?? ''] ?? selected.launch_status ?? '—'}</strong> · на сайте: {selected.places_published}/{selected.places_total}</p>
          <p>Обработано: {selected.processed_items ?? 0}/{selected.total_items ?? 0} · Успешно: {selected.successful_items ?? 0} · Ошибок: {selected.failed_items ?? 0}</p>
          <p>Найдено: {selected.places_found ?? 0} · Сохранено: {selected.places_saved ?? 0} · В городе: {selected.places_total}</p>
          {selected.last_error && <p className="admin-error-text">Ошибка: {selected.last_error}</p>}
          {selected.is_stalled && <p className="admin-error-text">Задача не обновлялась дольше порога — возможно зависла.</p>}
          <p>{selected.next_step}</p>
          {selected.step_details && (
            <div className="admin-muted">
              {detailLine('Найдено мест', selected.step_details['places_found'])}
              {detailLine('Сохранено мест', selected.step_details['places_saved'])}
              {detailLine('Всего к обработке', selected.step_details['total_items'])}
              {detailLine('Обработано', selected.step_details['processed_items'])}
            </div>
          )}
          <div className="admin-actions-cell">
            {selected.can_run && <button type="button" className="admin-btn admin-btn-sm" disabled={busy === selected.city_id} onClick={() => runAction(selected.city_id, `/admin/import-jobs/${selected.city_id}/run`, 'Собрать и обогатить город')}>Собрать и обогатить</button>}
            {selected.can_retry && <button type="button" className="admin-btn admin-btn-sm admin-btn-muted" disabled={busy === selected.city_id} onClick={() => runAction(selected.city_id, `/admin/import-jobs/${selected.city_id}/retry`, 'Повторить полный запуск')}>Повторить</button>}
            {selected.can_cancel && <button type="button" className="admin-btn admin-btn-sm admin-btn-danger" disabled={busy === selected.city_id} onClick={() => runAction(selected.city_id, `/admin/import-jobs/${selected.city_id}/cancel`, 'Отменить задачу')}>Отменить</button>}
            {selected.can_publish && <button type="button" className="admin-btn admin-btn-sm" disabled={busy === selected.city_id} onClick={() => runAction(selected.city_id, `/admin/import-jobs/${selected.city_id}/publish`, 'Опубликовать город')}>Опубликовать город</button>}
            {selected.report_url && <Link className="admin-btn admin-btn-sm" to={selected.report_url}>Отчёт качества</Link>}
            {selected.logs_url && <Link className="admin-btn admin-btn-sm" to={selected.logs_url}>Логи</Link>}
            <Link className="admin-btn admin-btn-sm" to={`/admin/places?city=${selected.city_slug}`}>Места</Link>
            <button type="button" className="admin-btn admin-btn-sm admin-btn-muted" onClick={() => setSelected(null)}>Закрыть</button>
          </div>
        </div>
      )}
    </div>
  )
}
