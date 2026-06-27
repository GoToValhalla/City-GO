import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminPost } from './adminApi'
import { adminDownload } from './adminDownload'
import { STATUS_LABEL, batchFilePath } from './adminEnrichmentHelpers'
import type { EnrichmentBatchMeta, ImportApplyResult, ImportPreviewResult } from './adminEnrichmentTypes'

type Props = { batches: EnrichmentBatchMeta[]; onRefresh: () => void }

export const AdminEnrichmentBatchTable = ({ batches, onRefresh }: Props) => {
  const [params, setParams] = useSearchParams()
  const selectedBatch = params.get('batch')
  const [preview, setPreview] = useState<ImportPreviewResult | null>(null)
  const [applyResult, setApplyResult] = useState<ImportApplyResult | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [downloading, setDownloading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const selectBatch = (batch: EnrichmentBatchMeta) => {
    const next = new URLSearchParams(params)
    next.set('batch', batch.batch_id)
    next.set('city', batch.city_slug)
    setParams(next)
  }

  const setBatchView = (batchId: string, view: string) => {
    const next = new URLSearchParams(params)
    next.set('batch', batchId)
    next.set('view', view)
    setParams(next)
  }

  const runPreview = async (batchId: string) => {
    setBusy(`preview:${batchId}`)
    setError(null)
    try {
      const r = await adminPost<ImportPreviewResult>(`/admin/place-enrichment/batches/${batchId}/preview`)
      setPreview(r)
      onRefresh()
      setBatchView(batchId, 'preview')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка предварительной проверки')
    } finally {
      setBusy(null)
    }
  }

  const runApply = async (batchId: string) => {
    const ok = window.confirm('Применить проверенные изменения к местам?')
    if (!ok) return
    setBusy(`apply:${batchId}`)
    setError(null)
    try {
      const r = await adminPost<ImportApplyResult>(`/admin/place-enrichment/batches/${batchId}/apply`)
      setApplyResult(r)
      onRefresh()
      setBatchView(batchId, 'result')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка применения')
    } finally {
      setBusy(null)
    }
  }

  const downloadFile = async (batchId: string, file: string) => {
    const key = `${batchId}:${file}`
    setDownloading(key)
    setError(null)
    try {
      await adminDownload(batchFilePath(batchId, file), file)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка скачивания')
    } finally {
      setDownloading(null)
    }
  }

  if (!batches.length) return <div className="admin-state">Пакетов пока нет</div>

  return <div>
    {error && <div className="admin-state admin-state-error">{error}</div>}
    <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Пакет</th><th>Статус</th><th>Город</th><th>Мест</th><th>Поля</th><th>Артефакты</th><th>Действия</th></tr></thead><tbody>{batches.map((b) => {
      const hasEnriched = ['enriched', 'previewed', 'imported'].includes(b.status)
      const canPreview = hasEnriched && b.status !== 'imported'
      const canApply = b.status === 'previewed'
      const active = selectedBatch === b.batch_id
      const actionBusy = busy?.endsWith(`:${b.batch_id}`) ?? false
      return <tr key={b.batch_id} className={active ? 'admin-row-highlight' : ''}><td><button type="button" className="admin-btn admin-btn-sm" onClick={() => selectBatch(b)}>Пакет {b.batch_id.slice(0, 8)} →</button><div className="admin-muted">{new Date(b.created_at).toLocaleString('ru-RU')}</div></td><td>{STATUS_LABEL[b.status] ?? b.status}</td><td><Link to={`/admin/cities/${b.city_slug}?tab=enrichment`}>{b.city_slug}</Link></td><td><Link to={`/admin/places?city=${b.city_slug}`}>{b.total_exported}</Link></td><td>{b.missing_fields.join(', ') || 'Не указаны'}</td><td className="admin-actions-cell"><button type="button" className="admin-btn admin-btn-sm" disabled={downloading === `${b.batch_id}:export.csv`} onClick={() => void downloadFile(b.batch_id, 'export.csv')}>Исходные данные</button>{hasEnriched && <button type="button" className="admin-btn admin-btn-sm" disabled={downloading === `${b.batch_id}:enriched.csv`} onClick={() => void downloadFile(b.batch_id, 'enriched.csv')}>Обогащённые данные</button>}{b.status === 'previewed' && <button type="button" className="admin-btn admin-btn-sm" onClick={() => void downloadFile(b.batch_id, 'import.preview.json')}>Предпросмотр</button>}{b.status === 'imported' && <button type="button" className="admin-btn admin-btn-sm" onClick={() => void downloadFile(b.batch_id, 'import.result.json')}>Результат</button>}</td><td className="admin-actions-cell">{!hasEnriched && <span className="admin-muted">Ожидается enriched.csv</span>}{canPreview && <button className="admin-btn admin-btn-sm" disabled={actionBusy} onClick={() => void runPreview(b.batch_id)}>{busy === `preview:${b.batch_id}` ? 'Проверяем…' : 'Проверить'}</button>}{canApply && <button className="admin-btn admin-btn-sm admin-btn-primary" disabled={actionBusy} onClick={() => void runApply(b.batch_id)}>{busy === `apply:${b.batch_id}` ? 'Применяем…' : 'Применить'}</button>}</td></tr>
    })}</tbody></table></div>
    {selectedBatch && <div className="admin-detail-panel"><h3>Пакет {selectedBatch}</h3><div className="admin-actions-cell"><Link className="admin-btn admin-btn-sm" to={`/admin/audit?entity_type=place_enrichment_batch&entity_id=${selectedBatch}`}>История пакета</Link><Link className="admin-btn admin-btn-sm" to={`/admin/system-logs?q=${encodeURIComponent(selectedBatch)}`}>Логи пакета</Link></div></div>}
    {preview && <div className="admin-detail-panel"><strong>Предпросмотр:</strong> {preview.rows_with_changes} строк с изменениями<Link className="admin-btn admin-btn-sm" to={`/admin/places?city=${params.get('city') ?? ''}&verification=needs_recheck`}>Открыть места на проверке</Link></div>}
    {applyResult && <div className="admin-detail-panel"><strong>Импортировано:</strong> {applyResult.rows_updated} мест · поля: {JSON.stringify(applyResult.fields_updated)}<Link className="admin-btn admin-btn-sm" to={`/admin/places?city=${params.get('city') ?? ''}&verification=needs_recheck`}>Открыть результат</Link></div>}
  </div>
}