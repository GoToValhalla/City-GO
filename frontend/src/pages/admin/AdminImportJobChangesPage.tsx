import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { adminGet } from './adminApi'
import type { AdminImportJob, AdminImportJobChangesResponse, AdminImportJobChangesSummary, AdminImportJobsResponse } from './adminTypes'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

const tabs = [
  ['created', 'Новые'],
  ['updated', 'Обновлённые'],
  ['needs_review', 'На проверку'],
  ['rejected', 'Отклонённые'],
  ['hidden', 'Скрытые'],
  ['unchanged', 'Без изменений'],
] as const
const badge: Record<string, string> = { created: 'Добавлено этим импортом', updated: 'Обновлено', needs_review: 'На проверку', rejected: 'Отклонено', hidden: 'Скрыто', unchanged: 'Без изменений' }

export const AdminImportJobChangesPage = () => {
  const { citySlug = '', jobId = '' } = useParams()
  const [params, setParams] = useSearchParams()
  const active = params.get('type') || 'created'
  const [cityId, setCityId] = useState<number | null>(Number(params.get('city_id')) || null)
  const [summary, setSummary] = useState<AdminImportJobChangesSummary | null>(null)
  const [rows, setRows] = useState<AdminImportJobChangesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const resolveCity = useCallback(async () => {
    if (cityId) return cityId
    const response = await adminGet<AdminImportJobsResponse>('/admin/import-jobs?limit=200')
    const match = response.items.find((item: AdminImportJob) => item.city_slug === citySlug && String(item.job_id ?? '') === jobId)
    if (!match) throw new Error('Запуск импорта не найден')
    setCityId(match.city_id)
    return match.city_id
  }, [cityId, citySlug, jobId])
  useEffect(() => {
    let alive = true
    setLoading(true); setError(null)
    resolveCity().then(async (id) => {
      const [nextSummary, nextRows] = await Promise.all([
        adminGet<AdminImportJobChangesSummary>(`/admin/import-jobs/${id}/changes/summary`),
        adminGet<AdminImportJobChangesResponse>(`/admin/import-jobs/${id}/changes?change_type=${active}&limit=50`),
      ])
      if (alive) { setSummary(nextSummary); setRows(nextRows) }
    }).catch((e: Error) => alive && setError(e.message)).finally(() => alive && setLoading(false))
    return () => { alive = false }
  }, [active, resolveCity])
  const counts = useMemo(() => tabs.map(([key, label]) => [key, label, summary?.[key] ?? 0] as const), [summary])
  const choose = (key: string) => { const next = new URLSearchParams(params); next.set('type', key); if (cityId) next.set('city_id', String(cityId)); setParams(next) }
  return <div>
    <h2 className="admin-page-title">Изменения импорта #{jobId}</h2>
    <p className="admin-page-subtitle">Город: {citySlug}. Это срез конкретного запуска, а не вся очередь проверки.</p>
    {error && <AdminError message={error} />}{loading ? <AdminLoading /> : !summary ? <AdminEmpty message="Отчёт не найден" /> : <>
      <div className="admin-metrics-grid">{counts.map(([key, label, value]) => <button type="button" className="admin-metric-card" key={key} onClick={() => choose(key)}><strong>{label}</strong><div className="admin-metric-value">{value}</div></button>)}</div>
      <div className="admin-actions-cell">{tabs.map(([key, label]) => <button key={key} type="button" className={`admin-btn admin-btn-sm ${active === key ? 'admin-btn-primary' : ''}`} onClick={() => choose(key)}>{label}</button>)}</div>
      {!rows?.items.length ? <AdminEmpty message="Для выбранного типа изменений записей нет" /> : <div className="admin-grid">{rows.items.map((row) => <article className="admin-action-card" key={row.id}>
        <span className="admin-badge pub-needs_review">{badge[row.change_type] ?? row.change_type}</span>
        <strong>{row.place_title || row.external_source_id || `Запись #${row.id}`}</strong>
        <span>{row.category || 'Без категории'} · {row.source || 'источник не указан'}</span>
        {row.reason && <span className="admin-muted">{row.reason}</span>}
        {row.place_id ? <Link className="admin-btn admin-btn-sm" to={`/admin/places/${row.place_id}`}>Открыть место</Link> : <span className="admin-muted">Место не создано</span>}
      </article>)}</div>}
    </>}
  </div>
}
