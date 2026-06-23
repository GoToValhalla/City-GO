import { Link } from 'react-router-dom'
import type { AdminCityWorkspaceResponse } from './adminTypes'

type Props = {
  data: AdminCityWorkspaceResponse
  busy: string | null
  onImportAction: (action: string) => void
  onPublish: () => void
  onUnpublish: () => void
}

const actionLabel: Record<string, string> = {
  run: 'Собрать и обогатить',
  retry: 'Повторить полный запуск',
  cancel: 'Отменить',
}

export const AdminCityWorkspacePanels = ({ data, busy, onImportAction, onPublish, onUnpublish }: Props) => {
  const job = data.import_job
  const coverage = data.coverage

  return (
    <>
      <div className="admin-metrics-grid admin-metrics-small">
        <div className="admin-metric-card"><div className="admin-metric-value">{data.city.launch_status}</div><div className="admin-metric-label">Статус города</div></div>
        <div className="admin-metric-card"><div className="admin-metric-value">{data.readiness.readiness_score}%</div><div className="admin-metric-label">Готовность · {data.readiness.quality_status}</div></div>
        <div className="admin-metric-card"><div className="admin-metric-value">{data.city.places_total ?? 0}</div><div className="admin-metric-label">Мест всего</div></div>
        <div className="admin-metric-card"><div className="admin-metric-value">{data.city.places_published ?? 0}</div><div className="admin-metric-label">Опубликовано</div></div>
        <div className="admin-metric-card"><div className="admin-metric-value">{data.city.pending_photos ?? 0}</div><div className="admin-metric-label">Фото на проверке</div></div>
      </div>

      <div className="admin-detail-panel">
        <h3>Сбор и обогащение</h3>
        <p>Задача #{job.job_id ?? '—'} · {job.status} · {job.current_step_label ?? job.current_step}</p>
        <p>Найдено/сохранено: {job.places_found ?? 0}/{job.places_saved ?? 0} · обработано: {job.processed_items ?? 0}/{job.total_items ?? 0} · повторов: {job.retry_count ?? 0}</p>
        <p>Обновлено: {job.updated_at ?? '—'}</p>
        {job.last_error && <p className="admin-error-text">{job.last_error}</p>}
        <p>{job.next_step}</p>
        {job.step_details && <p className="admin-muted">Подробности: {JSON.stringify(job.step_details)}</p>}
        <div className="admin-actions-cell">
          {job.can_run && <button type="button" className="admin-btn admin-btn-sm" disabled={busy === 'run'} onClick={() => onImportAction('run')}>{actionLabel.run}</button>}
          {job.can_retry && <button type="button" className="admin-btn admin-btn-sm" disabled={busy === 'retry'} onClick={() => onImportAction('retry')}>{actionLabel.retry}</button>}
          {job.can_cancel && <button type="button" className="admin-btn admin-btn-sm admin-btn-danger" disabled={busy === 'cancel'} onClick={() => onImportAction('cancel')}>{actionLabel.cancel}</button>}
        </div>
      </div>

      <div className="admin-detail-panel">
        <h3>Публикация и качество</h3>
        <p>Без адреса: {coverage?.places_without_address ?? 0}, без фото: {coverage?.places_without_photo ?? 0}</p>
        <div className="admin-actions-cell">
          {data.city.can_publish && <button type="button" className="admin-btn admin-btn-sm" disabled={busy === 'publish'} onClick={onPublish}>Опубликовать</button>}
          {data.city.can_unpublish && <button type="button" className="admin-btn admin-btn-sm admin-btn-danger" disabled={busy === 'unpublish'} onClick={onUnpublish}>Снять с сайта</button>}
          <Link className="admin-btn admin-btn-sm" to={`/admin/places?city=${data.city.slug}`}>Места</Link>
          <Link className="admin-btn admin-btn-sm" to={`/admin/routes/data-quality?city=${data.city.slug}`}>Качество данных</Link>
          <Link className="admin-btn admin-btn-sm" to={`/admin/coverage?city=${data.city.slug}`}>Покрытие</Link>
        </div>
      </div>
    </>
  )
}
