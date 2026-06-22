import { useState } from 'react'
import { adminPost } from './adminApi'
import { adminDownload } from './adminDownload'
import { STATUS_LABEL, batchFilePath } from './adminEnrichmentHelpers'
import type { EnrichmentBatchMeta, ImportApplyResult, ImportPreviewResult } from './adminEnrichmentTypes'

type Props = {
  batches: EnrichmentBatchMeta[]
  onRefresh: () => void
}

export const AdminEnrichmentBatchTable = ({ batches, onRefresh }: Props) => {
  const [preview, setPreview] = useState<ImportPreviewResult | null>(null)
  const [applyResult, setApplyResult] = useState<ImportApplyResult | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [downloading, setDownloading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const runPreview = async (batchId: string) => {
    setBusy(batchId); setError(null)
    try {
      const r = await adminPost<ImportPreviewResult>(`/admin/place-enrichment/batches/${batchId}/preview`)
      setPreview(r); onRefresh()
    } catch (e) { setError(e instanceof Error ? e.message : 'Preview error') }
    finally { setBusy(null) }
  }

  const runApply = async (batchId: string) => {
    setBusy(batchId); setError(null)
    try {
      const r = await adminPost<ImportApplyResult>(`/admin/place-enrichment/batches/${batchId}/apply`)
      setApplyResult(r); onRefresh()
    } catch (e) { setError(e instanceof Error ? e.message : 'Apply error') }
    finally { setBusy(null) }
  }

  const downloadFile = async (batchId: string, file: string) => {
    const key = `${batchId}:${file}`
    setDownloading(key); setError(null)
    try {
      await adminDownload(batchFilePath(batchId, file), file)
    } catch (e) { setError(e instanceof Error ? e.message : 'Download error') }
    finally { setDownloading(null) }
  }

  if (!batches.length) return <div className="admin-state">Batch-экспортов пока нет</div>

  return (
    <div>
      {error && <div className="admin-state admin-state-error">{error}</div>}
      <table className="admin-table">
        <thead>
          <tr>
            <th>Batch ID</th><th>Status</th><th>Город</th><th>Мест</th>
            <th>Missing</th><th>Файлы</th><th>Import</th>
          </tr>
        </thead>
        <tbody>
          {batches.map((b) => {
            const hasEnriched = b.status === 'enriched' || b.status === 'previewed' || b.status === 'imported'
            const canPreview = hasEnriched && b.status !== 'imported'
            const canApply = b.status === 'previewed'
            return (
              <tr key={b.batch_id}>
                <td><code style={{ fontSize: 10 }}>{b.batch_id}</code></td>
                <td>{STATUS_LABEL[b.status] ?? b.status}</td>
                <td>{b.city_slug}</td>
                <td><strong>{b.total_exported}</strong></td>
                <td style={{ fontSize: 11 }}>{b.missing_fields.join(', ')}</td>
                <td style={{ fontSize: 11 }}>
                  <button
                    type="button"
                    className="admin-btn admin-btn-sm"
                    disabled={downloading === `${b.batch_id}:export.csv`}
                    onClick={() => void downloadFile(b.batch_id, 'export.csv')}
                  >
                    export
                  </button>
                  {hasEnriched && (
                    <button
                      type="button"
                      className="admin-btn admin-btn-sm"
                      disabled={downloading === `${b.batch_id}:enriched.csv`}
                      onClick={() => void downloadFile(b.batch_id, 'enriched.csv')}
                    >
                      enriched
                    </button>
                  )}
                  {b.status === 'previewed' && (
                    <button
                      type="button"
                      className="admin-btn admin-btn-sm"
                      disabled={downloading === `${b.batch_id}:import.preview.json`}
                      onClick={() => void downloadFile(b.batch_id, 'import.preview.json')}
                    >
                      preview
                    </button>
                  )}
                  {b.status === 'imported' && (
                    <button
                      type="button"
                      className="admin-btn admin-btn-sm"
                      disabled={downloading === `${b.batch_id}:import.result.json`}
                      onClick={() => void downloadFile(b.batch_id, 'import.result.json')}
                    >
                      result
                    </button>
                  )}
                </td>
                <td>
                  {!hasEnriched && <span style={{ fontSize: 11, color: '#888' }}>Ожидается enriched.csv</span>}
                  {canPreview && (
                    <button className="admin-btn admin-btn-sm" disabled={busy === b.batch_id} onClick={() => runPreview(b.batch_id)}>
                      Preview
                    </button>
                  )}
                  {canApply && (
                    <button className="admin-btn admin-btn-sm admin-btn-primary" disabled={busy === b.batch_id} onClick={() => runApply(b.batch_id)}>
                      Apply
                    </button>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      {preview && (
        <div className="admin-detail-panel" style={{ marginTop: 12 }}>
          <strong>Preview:</strong> {preview.rows_with_changes} строк с изменениями
          {Object.keys(preview.unsupported_fields).length > 0 && (
            <span> · skipped: {JSON.stringify(preview.unsupported_fields)}</span>
          )}
        </div>
      )}
      {applyResult && (
        <div className="admin-detail-panel" style={{ marginTop: 12, color: '#34c759' }}>
          ✓ Импортировано {applyResult.rows_updated} мест · поля: {JSON.stringify(applyResult.fields_updated)}
        </div>
      )}
    </div>
  )
}