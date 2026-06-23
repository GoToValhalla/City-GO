import { useState } from 'react'
import { adminPost } from './adminApi'
import { MISSING_FIELDS, type useEnrichmentForm } from './adminEnrichmentForm'
import type { EnrichmentExportMeta } from './adminEnrichmentTypes'
import { QUICK_EXPORT_FIELDS } from './adminEnrichmentTypes'

type Props = {
  form: ReturnType<typeof useEnrichmentForm>
  onExported: () => void
}

export const AdminLegacyEnrichmentPanel = ({ form, onExported }: Props) => {
  const [exporting, setExporting] = useState(false)
  const [quickExporting, setQuickExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)
  const [lastResult, setLastResult] = useState<EnrichmentExportMeta | null>(null)

  const doExport = async (payload: object, quick = false) => {
    if (!form.citySlug) return
    if (quick) setQuickExporting(true)
    if (!quick) setExporting(true)
    setExportError(null)
    try {
      const result = await adminPost<EnrichmentExportMeta>('/admin/place-enrichment/export', payload)
      setLastResult(result)
      onExported()
    } catch (e) {
      setExportError(e instanceof Error ? e.message : 'Ошибка экспорта')
    } finally {
      if (quick) setQuickExporting(false)
      if (!quick) setExporting(false)
    }
  }

  const chatgptPath = lastResult?.export_csv_path ?? (lastResult?.batch_id ? `data/exports/place_enrichment/active/${lastResult.batch_id}/export.csv` : null)

  return (
    <section className="admin-detail-panel">
      <h3>Ручной CSV-сценарий</h3>
      <p>Запасной способ: выгрузить CSV, обогатить во внешнем инструменте и импортировать enriched.csv.</p>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
        <button className="admin-btn admin-btn-primary" data-testid="quick-export-btn" disabled={quickExporting || !form.citySlug}
          onClick={() => void doExport({ city_slug: form.citySlug, limit: 100, only_published: true, only_route_eligible: false, missing_fields: QUICK_EXPORT_FIELDS, git_artifact: true }, true)}>
          {quickExporting ? 'Формируем...' : 'Сформировать стандартный экспорт'}
        </button>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
        {MISSING_FIELDS.map(({ key, label }) => <label key={key} style={{ fontSize: 13 }}><input type="checkbox" checked={form.selectedFields.includes(key)} onChange={() => form.toggleField(key)} /> {label}</label>)}
      </div>
      <button className="admin-btn" disabled={exporting || !form.citySlug}
        onClick={() => void doExport({ city_slug: form.citySlug, limit: form.limit, only_published: form.onlyPublished, only_route_eligible: form.onlyRouteEligible, missing_fields: form.selectedFields, git_artifact: true })}>
        {exporting ? 'Формируем CSV...' : 'Сформировать CSV для обогащения'}
      </button>
      {exportError && <div className="admin-state admin-state-error">{exportError}</div>}
      {chatgptPath && <div data-testid="chatgpt-path-hint" style={{ marginTop: 12, background: '#fffbe6', padding: 8, borderRadius: 6 }}>Путь для ручного сценария: <code>{chatgptPath}</code></div>}
    </section>
  )
}
