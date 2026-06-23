import { useCallback, useEffect, useState } from 'react'
import { adminGet } from './adminApi'
import { AdminEnrichmentBatchTable } from './AdminEnrichmentBatchTable'
import { AdminLegacyEnrichmentPanel } from './AdminLegacyEnrichmentPanel'
import { AdminPipelineEnrichmentPanel } from './AdminPipelineEnrichmentPanel'
import { useEnrichmentForm } from './adminEnrichmentForm'
import type { EnrichmentBatchMeta } from './adminEnrichmentTypes'

export const AdminPlaceEnrichmentPage = () => {
  const form = useEnrichmentForm()
  const [batches, setBatches] = useState<EnrichmentBatchMeta[]>([])
  const [batchesLoading, setBatchesLoading] = useState(true)
  const [batchesError, setBatchesError] = useState<string | null>(null)

  const loadBatches = useCallback(() => {
    setBatchesLoading(true)
    setBatchesError(null)
    return adminGet<{ items: EnrichmentBatchMeta[]; total: number }>('/admin/place-enrichment/batches')
      .then((r) => setBatches(r.items))
      .catch((e: Error) => setBatchesError(e.message))
      .finally(() => setBatchesLoading(false))
  }, [])

  useEffect(() => { void Promise.resolve().then(loadBatches) }, [loadBatches])

  return (
    <div>
      <h2 className="admin-page-title">Обогащение данных</h2>
      <p className="admin-page-subtitle">Основной сценарий: автоматическое обогащение. CSV оставлен как запасной ручной способ.</p>
      <AdminPipelineEnrichmentPanel form={form} />
      <AdminLegacyEnrichmentPanel form={form} onExported={loadBatches} />

      <h3 style={{ marginTop: 24 }}>История batch ({batches.length})</h3>
      {batchesError ? <div className="admin-state admin-state-error">{batchesError}</div> : null}
      {batchesLoading ? <div className="admin-state">Загружаем историю batch...</div> : null}
      <AdminEnrichmentBatchTable batches={batches} onRefresh={loadBatches} />
    </div>
  )
}
