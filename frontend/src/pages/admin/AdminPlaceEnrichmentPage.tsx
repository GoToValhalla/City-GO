import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { adminGet } from './adminApi'
import { AdminEnrichmentBatchTable } from './AdminEnrichmentBatchTable'
import { AdminLegacyEnrichmentPanel } from './AdminLegacyEnrichmentPanel'
import { AdminPipelineEnrichmentPanel } from './AdminPipelineEnrichmentPanel'
import { useEnrichmentForm } from './adminEnrichmentForm'
import type { EnrichmentBatchMeta } from './adminEnrichmentTypes'

export const AdminPlaceEnrichmentPage = () => {
  const [params] = useSearchParams(); const form = useEnrichmentForm(); const { citySlug, setCitySlug } = form; const [batches, setBatches] = useState<EnrichmentBatchMeta[]>([]); const [batchesLoading, setBatchesLoading] = useState(true); const [batchesError, setBatchesError] = useState<string | null>(null)
  const loadBatches = useCallback(() => { setBatchesLoading(true); setBatchesError(null); return adminGet<{ items: EnrichmentBatchMeta[]; total: number }>('/admin/place-enrichment/batches', { cache: false }).then((r) => setBatches(r.items)).catch((e: Error) => setBatchesError(e.message)).finally(() => setBatchesLoading(false)) }, [])
  useEffect(() => { void Promise.resolve().then(loadBatches) }, [loadBatches])
  useEffect(() => { const city = params.get('city'); if (city && city !== citySlug) setCitySlug(city) }, [params, citySlug, setCitySlug])
  const visibleBatches = params.get('city') ? batches.filter((batch) => batch.city_slug === params.get('city')) : batches
  return <div><h2 className="admin-page-title">Сбор и обогащение данных</h2><p className="admin-page-subtitle">Запуски, пакеты, шаги и результаты имеют постоянные URL и связаны с местами, логами и аудитом.</p><AdminPipelineEnrichmentPanel form={form} /><AdminLegacyEnrichmentPanel form={form} onExported={loadBatches} /><h3 style={{ marginTop: 24 }}>История ручных пакетов ({visibleBatches.length})</h3>{batchesError ? <div className="admin-state admin-state-error">{batchesError}</div> : null}{batchesLoading ? <div className="admin-state">Загружаем историю…</div> : null}{!batchesLoading ? <AdminEnrichmentBatchTable batches={visibleBatches} onRefresh={loadBatches} /> : null}</div>
}