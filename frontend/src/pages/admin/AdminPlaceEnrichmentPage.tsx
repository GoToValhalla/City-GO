import { useCallback, useEffect, useState } from 'react'
import { adminGet, adminPost } from './adminApi'
import { AdminEnrichmentBatchTable } from './AdminEnrichmentBatchTable'
import { MISSING_FIELDS, useEnrichmentForm } from './adminEnrichmentForm'
import type { EnrichmentBatchMeta, EnrichmentExportMeta } from './adminEnrichmentTypes'
import { QUICK_EXPORT_FIELDS } from './adminEnrichmentTypes'

export const AdminPlaceEnrichmentPage = () => {
  const form = useEnrichmentForm()
  const [exporting, setExporting] = useState(false)
  const [quickExporting, setQuickExporting] = useState(false)
  const [batches, setBatches] = useState<EnrichmentBatchMeta[]>([])
  const [exportError, setExportError] = useState<string | null>(null)
  const [lastResult, setLastResult] = useState<EnrichmentExportMeta | null>(null)

  const loadBatches = useCallback(() => {
    adminGet<{ items: EnrichmentBatchMeta[]; total: number }>('/admin/place-enrichment/batches')
      .then((r) => setBatches(r.items))
      .catch(() => {})
  }, [])

  useEffect(() => { void Promise.resolve().then(loadBatches) }, [loadBatches])

  const doExport = async (payload: object, quick = false) => {
    if (!form.citySlug) return
    if (quick) {
      setQuickExporting(true)
    } else {
      setExporting(true)
    }
    setExportError(null)
    try {
      const result = await adminPost<EnrichmentExportMeta>('/admin/place-enrichment/export', payload)
      setLastResult(result)
      loadBatches()
    } catch (e) {
      setExportError(e instanceof Error ? e.message : 'Ошибка экспорта')
    } finally {
      if (quick) {
        setQuickExporting(false)
      } else {
        setExporting(false)
      }
    }
  }

  const chatgptPath = lastResult?.export_csv_path ?? (
    lastResult?.batch_id
      ? `data/exports/place_enrichment/active/${lastResult.batch_id}/export.csv`
      : null
  )

  return (
    <div>
      <h2 className="admin-page-title">Обогащение данных</h2>
      <p className="admin-page-subtitle">Экспорт CSV → обогащение в ChatGPT → импорт enriched.csv обратно</p>

      <div className="admin-detail-panel" style={{ marginBottom: 16, background: '#f0f9ff', border: '1px solid #bae6fd' }}>
        <h3 style={{ marginTop: 0 }}>Как это работает</h3>
        <ol style={{ fontSize: 13, color: '#555', margin: '0 0 12px', paddingLeft: 20 }}>
          <li>Выберите город и поля для обогащения</li>
          <li>Сформируйте CSV — система создаст batch</li>
          <li>Обогатите данные во внешнем инструменте и сохраните как <code>enriched.csv</code></li>
          <li>Импортируйте файл в таблице batches ниже</li>
        </ol>
        <h3>⚡ Быстрый экспорт</h3>
        <p style={{ fontSize: 13, color: '#555' }}>Поля: адрес, фото, описание · лимит 100 мест</p>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <select value={form.citySlug} onChange={e => form.setCitySlug(e.target.value)} style={{ padding: '7px 11px', borderRadius: 7, border: '1px solid #d1d1d6' }}>
            {form.cities.map(c => <option key={c.id} value={c.slug}>{c.name}</option>)}
          </select>
          <button className="admin-btn admin-btn-primary" data-testid="quick-export-btn"
            disabled={quickExporting || !form.citySlug}
            onClick={() => void doExport({ city_slug: form.citySlug, limit: 100, only_published: true, only_route_eligible: false, missing_fields: QUICK_EXPORT_FIELDS, git_artifact: true }, true)}>
            {quickExporting ? 'Формируем...' : 'Сформировать стандартный экспорт'}
          </button>
        </div>
      </div>

      <div className="admin-detail-panel">
        <h3>Кастомный экспорт</h3>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
          {MISSING_FIELDS.map(({ key, label }) => (
            <label key={key} style={{ fontSize: 13 }}>
              <input type="checkbox" checked={form.selectedFields.includes(key)} onChange={() => form.toggleField(key)} /> {label}
            </label>
          ))}
        </div>
        <button className="admin-btn admin-btn-primary" disabled={exporting || !form.citySlug}
          onClick={() => void doExport({ city_slug: form.citySlug, limit: form.limit, only_published: form.onlyPublished, only_route_eligible: form.onlyRouteEligible, missing_fields: form.selectedFields, git_artifact: true })}>
          {exporting ? 'Формируем CSV...' : 'Сформировать CSV для обогащения'}
        </button>
        {exportError && <div className="admin-state admin-state-error">{exportError}</div>}
        {lastResult && (
          <div style={{ marginTop: 12, fontSize: 13 }}>
            <div style={{ color: '#34c759' }}>✓ Batch: <code>{lastResult.batch_id ?? lastResult.export_id}</code> · {lastResult.total_exported} мест</div>
            {chatgptPath && (
              <div data-testid="chatgpt-path-hint" style={{ marginTop: 6, background: '#fffbe6', padding: 8, borderRadius: 6 }}>
                Передайте ChatGPT путь: <code>{chatgptPath}</code>
              </div>
            )}
          </div>
        )}
      </div>

      <h3 style={{ marginTop: 24 }}>История batch ({batches.length})</h3>
      <AdminEnrichmentBatchTable batches={batches} onRefresh={loadBatches} />
    </div>
  )
}
