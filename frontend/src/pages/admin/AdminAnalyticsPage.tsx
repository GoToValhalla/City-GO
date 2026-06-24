import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { adminGet } from './adminApi'
import type { AnalyticsPayload } from './adminPlatformTypes'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

const TABS = ['Обзор', 'Города', 'Места', 'Маршруты', 'Воронки', 'Качество данных', 'Импорты', 'Производительность']
const METRIC_LABELS: Record<string, string> = {
  active_users: 'Активные пользователи',
  average_route_points: 'Среднее число точек',
  content_view_share: 'Доля просмотров мест',
  event_count: 'Всего событий',
  place_views: 'Просмотры мест',
  route_builds: 'Построения маршрутов',
  route_success_rate: 'Успешные маршруты, %',
}
const EVENT_LABELS: Record<string, string> = {
  place_viewed: 'Просмотр места',
  route_build_failed: 'Ошибка построения маршрута',
  route_build_succeeded: 'Успешное построение маршрута',
  route_started: 'Маршрут начат',
}

export const AdminAnalyticsPage = () => {
  const [params, setParams] = useSearchParams()
  const [data, setData] = useState<AnalyticsPayload | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const load = useCallback(() => {
    setLoading(true)
    adminGet<AnalyticsPayload>(`/admin/analytics?${params}`).then(setData)
      .catch((e: Error) => setError(e.message)).finally(() => setLoading(false))
  }, [params])
  useEffect(() => { void Promise.resolve().then(load) }, [load])
  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next)
  }
  return <div>
    <h2 className="admin-page-title">Аналитика</h2><p className="admin-page-subtitle">Сводные показатели пользовательских событий и построения маршрутов без передачи исходных записей.</p>
    <div className="admin-tabs">{TABS.map((tab) => <button className={`admin-tab${(params.get('tab') ?? 'Обзор') === tab ? ' active' : ''}`} onClick={() => update('tab', tab)} key={tab}>{tab}</button>)}</div>
    <div className="admin-filter-card admin-filter-grid"><label className="admin-field"><span>Период</span><select value={params.get('days') ?? '30'} onChange={(e) => update('days', e.target.value)}><option value="7">7 дней</option><option value="30">30 дней</option><option value="90">90 дней</option></select></label><label className="admin-field"><span>Город</span><input value={params.get('city_slug') ?? ''} onChange={(e) => update('city_slug', e.target.value)} /></label><label className="admin-field"><span>Регион</span><input value={params.get('region') ?? ''} onChange={(e) => update('region', e.target.value)} /></label><label className="admin-field"><span>Категория</span><input value={params.get('category') ?? ''} onChange={(e) => update('category', e.target.value)} /></label><label className="admin-field"><span>Канал</span><select value={params.get('channel') ?? ''} onChange={(e) => update('channel', e.target.value)}><option value="">Все</option><option value="web">Веб</option><option value="telegram">Telegram</option></select></label><label className="admin-field"><span>Окружение</span><input value={params.get('environment') ?? ''} onChange={(e) => update('environment', e.target.value)} /></label></div>
    {error && <AdminError message={error} />}{loading ? <AdminLoading /> : !data ? <AdminEmpty message="Недостаточно данных" /> : <><div className="admin-metrics-grid">{Object.entries(data.metrics).map(([key, value]) => <div className="admin-metric-card" key={key}><div className="admin-metric-value">{value ?? 'Недостаточно данных'}</div><div className="admin-metric-label">{METRIC_LABELS[key] ?? 'Дополнительный показатель'}</div></div>)}</div><section className="admin-detail-panel"><h3>События</h3>{data.event_breakdown.map((row) => <p key={row.event}>{EVENT_LABELS[row.event] ?? 'Другое событие'}: {row.count}</p>)}</section></>}
  </div>
}
