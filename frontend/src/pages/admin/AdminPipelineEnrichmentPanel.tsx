import { useState } from 'react'
import { adminGet, adminPost } from './adminApi'
import type { ImportJobStep, PipelineRunResponse, ReviewQueueItem } from './adminEnrichmentTypes'
import type { useEnrichmentForm } from './adminEnrichmentForm'
import { counterLabels, fieldLabel, reasonLabel, statusLabel, stepLabel } from './adminPipelineLabels'

type Props = { form: ReturnType<typeof useEnrichmentForm> }

export const AdminPipelineEnrichmentPanel = ({ form }: Props) => {
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<PipelineRunResponse | null>(null)
  const [steps, setSteps] = useState<ImportJobStep[]>([])
  const [review, setReview] = useState<ReviewQueueItem[]>([])
  const [reviewLoading, setReviewLoading] = useState(false)
  const [reviewError, setReviewError] = useState<string | null>(null)
  const [resolvingId, setResolvingId] = useState<number | null>(null)

  const loadReview = async () => {
    if (!form.citySlug) return
    setReviewLoading(true)
    setReviewError(null)
    try {
      setReview(await adminGet<ReviewQueueItem[]>(`/admin/place-enrichment/review-queue?city_slug=${form.citySlug}`))
    } catch (e) {
      setReviewError(e instanceof Error ? e.message : 'Не удалось загрузить очередь проверки')
    } finally {
      setReviewLoading(false)
    }
  }

  const runPipeline = async () => {
    if (!form.citySlug) return
    setRunning(true)
    setError(null)
    setResult(null)
    setSteps([])
    try {
      const response = await adminPost<PipelineRunResponse>(`/admin/place-enrichment/pipeline/${form.citySlug}/run`)
      setResult(response)
      if (response.status !== 'queued') {
        setSteps(await adminGet<ImportJobStep[]>(`/admin/place-enrichment/jobs/${response.job_id}/steps`))
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка запуска полного сбора')
    } finally {
      setRunning(false)
    }
  }

  const resolveItem = async (id: number) => {
    setResolvingId(id)
    setReviewError(null)
    try {
      await adminPost<ReviewQueueItem>(`/admin/place-enrichment/review-queue/${id}/resolve`, { resolution: 'resolved_in_admin' })
      await loadReview()
    } catch (e) {
      setReviewError(e instanceof Error ? e.message : 'Не удалось закрыть задачу проверки')
    } finally {
      setResolvingId(null)
    }
  }

  return (
    <section className="admin-detail-panel" style={{ marginBottom: 16 }}>
      <h3>Сбор и обогащение города</h3>
      <p>Дособирает места из OSM по настроенным зонам, обновляет записи без дублей, затем ищет адреса, фото, описания, сайты, телефоны и часы работы.</p>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 12 }}>
        <select value={form.citySlug} onChange={e => form.setCitySlug(e.target.value)} style={{ padding: '7px 11px', borderRadius: 7, border: '1px solid #d1d1d6' }}>
          {form.cities.map(c => <option key={c.id} value={c.slug}>{c.name}</option>)}
        </select>
        <button className="admin-btn admin-btn-primary" disabled={running || !form.citySlug} onClick={() => void runPipeline()}>
          {running ? 'Ставим задачу в очередь...' : 'Собрать и обогатить'}
        </button>
        <button className="admin-btn" disabled={reviewLoading || !form.citySlug} onClick={() => void loadReview()}>
          {reviewLoading ? 'Загружаем...' : 'Обновить очередь проверки'}
        </button>
      </div>
      {error && <div className="admin-state admin-state-error">{error}</div>}
      {result && <PipelineSummary result={result} steps={steps} />}
      {reviewError && <div className="admin-state admin-state-error">{reviewError}</div>}
      {reviewLoading ? <div className="admin-state">Загрузка очереди проверки...</div> : <ReviewQueue items={review} resolvingId={resolvingId} onResolve={(id) => void resolveItem(id)} />}
    </section>
  )
}

const PipelineSummary = ({ result, steps }: { result: PipelineRunResponse; steps: ImportJobStep[] }) => (
  <div style={{ marginTop: 14 }}>
    <div className="admin-success-text">Задача #{result.job_id} · {statusLabel(result.status)}</div>
    {result.message && <div className="admin-state">{result.message}</div>}
    {Object.keys(result.counters).length > 0 && (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 8, marginTop: 10 }}>
        {Object.entries(result.counters).map(([key, value]) => <div key={key} className="admin-card"><strong>{counterLabels[key] ?? key}</strong><div>{value}</div></div>)}
      </div>
    )}
    {steps.length > 0 && <div style={{ marginTop: 10, fontSize: 13 }}>{steps.map(s => `${stepLabel(s.step_name)}: ${statusLabel(s.status)}`).join(' · ')}</div>}
  </div>
)

const ReviewQueue = ({ items, resolvingId, onResolve }: { items: ReviewQueueItem[]; resolvingId: number | null; onResolve: (id: number) => void }) => {
  if (!items.length) return <div className="admin-state">Открытых задач проверки нет</div>
  return <table className="admin-table" style={{ marginTop: 12 }}><thead><tr><th>Место</th><th>Поле</th><th>Причина</th><th /></tr></thead><tbody>
    {items.map(i => <tr key={i.id}><td>{i.place_id}</td><td>{fieldLabel(i.field_name)}</td><td>{reasonLabel(i.reason)}</td><td><button className="admin-btn admin-btn-sm" disabled={resolvingId === i.id} onClick={() => onResolve(i.id)}>{resolvingId === i.id ? 'Закрываем...' : 'Закрыть'}</button></td></tr>)}
  </tbody></table>
}
