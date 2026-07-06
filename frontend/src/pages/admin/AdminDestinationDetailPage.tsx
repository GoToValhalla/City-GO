import { type FormEvent, useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { adminGet, adminPost, adminPostLong } from './adminApi'
import { AdminLoading, AdminSectionError } from './shared/AdminStates'
import './AdminDataPipeline.css'

type DestinationDetail = {
  slug: string
  title: string
  destination_type: string
  places_count: number
  scopes: { id: number; code: string; name: string; scope_type: string; enabled: boolean }[]
}

type MembershipRow = {
  id: number
  place_id: number
  assignment_type: string
  is_primary: boolean
  is_hidden: boolean
}

type OrphanRow = { id: number; slug: string; title: string }
type PipelineRun = {
  id: number
  status: string
  stage: string
  mode: string
  counters: Record<string, number>
  message?: string
  finished_at?: string | null
}
type Readiness = {
  readiness_score: number
  places_total: number
  published_places: number
  route_eligible_places: number
  service_only_hidden: number
  pending_reviews: number
  address_coverage_pct: number
  photo_coverage_pct: number
  description_coverage_pct: number
  coordinates_coverage_pct: number
  opening_hours_coverage_pct: number
  degraded_sections: string[]
  last_pipeline_run_status?: string | null
}
type ReviewRow = { id: number; place_id: number; place_name: string; reason?: string | null }

const TYPE_LABELS: Record<string, string> = {
  city: 'Город',
  region: 'Регион',
  natural_region: 'Природный регион',
  national_park: 'Национальный парк',
  tourist_cluster: 'Туристический кластер',
  route_corridor: 'Коридор маршрута',
  remote_area: 'Удалённая территория',
}

export const AdminDestinationDetailPage = () => {
  const { slug = '' } = useParams()
  const [detail, setDetail] = useState<DestinationDetail | null>(null)
  const [memberships, setMemberships] = useState<MembershipRow[]>([])
  const [orphans, setOrphans] = useState<OrphanRow[]>([])
  const [readiness, setReadiness] = useState<Readiness | null>(null)
  const [latestRun, setLatestRun] = useState<PipelineRun | null>(null)
  const [runHistory, setRunHistory] = useState<PipelineRun[]>([])
  const [reviews, setReviews] = useState<ReviewRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [scopeCode, setScopeCode] = useState('catalog-core')
  const [scopeName, setScopeName] = useState('Основной каталог')
  const [scopeBbox, setScopeBbox] = useState('{"south":54.5,"north":55.0,"west":20.0,"east":21.0}')
  const [assignPlaceId, setAssignPlaceId] = useState('')
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [action, setAction] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!slug) return
    setLoading(true)
    setError(null)
    try {
      const [dest, mem, orph, ready, latest, history, reviewItems] = await Promise.all([
        adminGet<DestinationDetail>(`/admin/destinations/${slug}`),
        adminGet<MembershipRow[]>(`/admin/destinations/${slug}/memberships`),
        adminGet<OrphanRow[]>('/admin/destinations/orphans/places?limit=20'),
        adminGet<Readiness>(`/admin/destinations/${slug}/readiness`),
        adminGet<{ run: PipelineRun } | null>(`/admin/destinations/${slug}/data-pipeline/latest`),
        adminGet<{ items: PipelineRun[] }>(`/admin/destinations/${slug}/data-pipeline/runs`),
        adminGet<ReviewRow[]>(`/admin/destinations/${slug}/review-items`),
      ])
      setDetail(dest)
      setMemberships(mem)
      setOrphans(orph)
      setReadiness(ready)
      setLatestRun(latest?.run ?? null)
      setRunHistory(history.items)
      setReviews(reviewItems)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить направление')
    } finally {
      setLoading(false)
    }
  }, [slug])

  useEffect(() => { void load() }, [load])

  const runPipeline = async (mode: string) => {
    setAction(mode)
    setFormError(null)
    setNotice(null)
    try {
      const data = await adminPostLong<{ message: string }>(`/admin/destinations/${slug}/data-pipeline/run`, { mode })
      setNotice(data.message)
      await load()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Не удалось запустить прогон')
    } finally {
      setAction(null)
    }
  }

  const recalculateMemberships = async () => {
    setAction('recalc')
    setFormError(null)
    setNotice(null)
    try {
      const data = await adminPost<{ message: string }>(`/admin/destinations/${slug}/memberships/recalculate`)
      setNotice(data.message)
      await load()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Не удалось пересчитать принадлежность')
    } finally {
      setAction(null)
    }
  }

  const onCreateScope = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setFormError(null)
    try {
      const bbox = JSON.parse(scopeBbox) as Record<string, number>
      await adminPost(`/admin/destinations/${slug}/scopes`, {
        code: scopeCode,
        name: scopeName,
        scope_type: 'catalog',
        import_strategy: 'single_bbox',
        bbox,
        enabled: true,
      })
      await load()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Не удалось создать контур')
    } finally {
      setSaving(false)
    }
  }

  const onAssignPlace = async (e: FormEvent) => {
    e.preventDefault()
    const placeId = Number(assignPlaceId)
    if (!Number.isFinite(placeId)) {
      setFormError('Укажите числовой идентификатор места')
      return
    }
    setSaving(true)
    setFormError(null)
    try {
      await adminPost(`/admin/destinations/${slug}/assign-place`, { place_id: placeId, is_primary: false })
      setAssignPlaceId('')
      await load()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Не удалось назначить место')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <AdminLoading message="Загрузка направления…" />
  if (error || !detail) {
    return <AdminSectionError title="Ошибка" message={error ?? 'Направление не найдено'} onRetry={() => void load()} />
  }

  return (
    <div className="admin-data-pipeline" data-testid="admin-destination-detail">
      <header className="admin-page-header">
        <div>
          <p className="admin-page-subtitle"><Link to="/admin/destinations">← Направления</Link></p>
          <h1 className="admin-page-title">{detail.title}</h1>
          <p className="admin-page-subtitle">
            {TYPE_LABELS[detail.destination_type] ?? detail.destination_type} · {detail.places_count} мест
          </p>
        </div>
      </header>

      {formError ? <div className="admin-state admin-state-error">{formError}</div> : null}
      {notice ? <div className="admin-state admin-state-success">{notice}</div> : null}

      <section className="admin-section">
        <h2 className="admin-section-title">Рабочее пространство данных</h2>
        <div className="admin-metric-grid">
          <article className="admin-metric-card"><span>Готовность</span><strong>{readiness?.readiness_score ?? 0}%</strong></article>
          <article className="admin-metric-card"><span>Мест</span><strong>{readiness?.places_total ?? detail.places_count}</strong></article>
          <article className="admin-metric-card"><span>Опубликовано</span><strong>{readiness?.published_places ?? 0}</strong></article>
          <article className="admin-metric-card"><span>Для маршрутов</span><strong>{readiness?.route_eligible_places ?? 0}</strong></article>
          <article className="admin-metric-card"><span>Скрыто служебных</span><strong>{readiness?.service_only_hidden ?? 0}</strong></article>
          <article className="admin-metric-card"><span>Проверки</span><strong>{readiness?.pending_reviews ?? reviews.length}</strong></article>
        </div>
        <div className="admin-action-row">
          <button type="button" className="admin-btn admin-btn-safe" disabled={Boolean(action)} onClick={() => void runPipeline('full')}>{action === 'full' ? 'Запуск…' : 'Запустить полный сбор данных'}</button>
          <button type="button" className="admin-btn" disabled={Boolean(action)} onClick={() => void runPipeline('import_only')}>Только импорт</button>
          <button type="button" className="admin-btn" disabled={Boolean(action)} onClick={() => void runPipeline('enrich_only')}>Только обогащение</button>
          <button type="button" className="admin-btn" disabled={Boolean(action)} onClick={() => void recalculateMemberships()}>Пересчитать принадлежность мест</button>
        </div>
        <p className="admin-page-subtitle">Последний прогон: {latestRun ? `${statusLabel(latestRun.status)} · ${stageLabel(latestRun.stage)}` : 'ещё не запускался'}</p>
        <p><a href={`/places?destination_slug=${detail.slug}`}>Открыть публичный каталог направления</a></p>
      </section>

      <section className="admin-section">
        <h2 className="admin-section-title">Покрытие данных</h2>
        <div className="admin-metric-grid">
          <article className="admin-metric-card"><span>Адреса</span><strong>{readiness?.address_coverage_pct ?? 0}%</strong></article>
          <article className="admin-metric-card"><span>Фото</span><strong>{readiness?.photo_coverage_pct ?? 0}%</strong></article>
          <article className="admin-metric-card"><span>Описания</span><strong>{readiness?.description_coverage_pct ?? 0}%</strong></article>
          <article className="admin-metric-card"><span>Координаты</span><strong>{readiness?.coordinates_coverage_pct ?? 0}%</strong></article>
          <article className="admin-metric-card"><span>Время работы</span><strong>{readiness?.opening_hours_coverage_pct ?? 0}%</strong></article>
        </div>
        {readiness?.degraded_sections.length ? <p className="admin-state-warning">Требуют внимания: {readiness.degraded_sections.map(sectionLabel).join(', ')}</p> : null}
      </section>

      <section className="admin-section">
        <h2 className="admin-section-title">Контуры</h2>
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Код</th><th>Название</th><th>Тип</th><th>Статус</th></tr></thead>
            <tbody>
              {detail.scopes.map((s) => (
                <tr key={s.id}><td>{s.code}</td><td>{s.name}</td><td>{scopeTypeLabel(s.scope_type)}</td><td>{s.enabled ? 'Включён' : 'Выключен'}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <form className="admin-form-grid" onSubmit={(e) => void onCreateScope(e)}>
          <input value={scopeCode} onChange={(e) => setScopeCode(e.target.value)} placeholder="Код контура" required />
          <input value={scopeName} onChange={(e) => setScopeName(e.target.value)} placeholder="Название" required />
          <textarea value={scopeBbox} onChange={(e) => setScopeBbox(e.target.value)} rows={3} aria-label="BBox JSON" />
          <button type="submit" className="admin-btn admin-btn-safe" disabled={saving}>{saving ? 'Сохранение…' : 'Добавить контур'}</button>
        </form>
      </section>

      <section className="admin-section">
        <h2 className="admin-section-title">Членства мест</h2>
        <div className="admin-table-wrap">
          <table className="admin-table" data-testid="memberships-table">
            <thead><tr><th>Место</th><th>Тип</th><th>Основное</th><th>Скрыто</th></tr></thead>
            <tbody>
              {memberships.map((m) => (
                <tr key={m.id}>
                  <td>{m.place_id}</td>
                  <td>{assignmentLabel(m.assignment_type)}</td>
                  <td>{m.is_primary ? 'Да' : 'Нет'}</td>
                  <td>{m.is_hidden ? 'Да' : 'Нет'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <form className="admin-form-grid" onSubmit={(e) => void onAssignPlace(e)}>
          <input value={assignPlaceId} onChange={(e) => setAssignPlaceId(e.target.value)} placeholder="ID места" />
          <button type="submit" className="admin-btn admin-btn-safe" disabled={saving}>Назначить вручную</button>
        </form>
      </section>

      <section className="admin-section">
        <h2 className="admin-section-title">История прогонов</h2>
        <div className="admin-table-wrap">
          <table className="admin-table" data-testid="pipeline-history-table">
            <thead><tr><th>ID</th><th>Режим</th><th>Статус</th><th>Этап</th><th>Найдено</th><th>Создано</th></tr></thead>
            <tbody>
              {runHistory.map((run) => (
                <tr key={run.id}><td>{run.id}</td><td>{modeLabel(run.mode)}</td><td>{statusLabel(run.status)}</td><td>{stageLabel(run.stage)}</td><td>{run.counters.candidates_found ?? 0}</td><td>{run.counters.places_created ?? 0}</td></tr>
              ))}
              {!runHistory.length ? <tr><td colSpan={6}>Прогонов пока нет</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="admin-section">
        <h2 className="admin-section-title">Заявки на проверку</h2>
        <div className="admin-table-wrap">
          <table className="admin-table" data-testid="destination-reviews-table">
            <thead><tr><th>ID</th><th>Место</th><th>Причина</th><th /></tr></thead>
            <tbody>
              {reviews.map((item) => (
                <tr key={item.id}><td>{item.id}</td><td>{item.place_name}</td><td>{reasonLabel(item.reason)}</td><td><Link to="/admin/reviews">Открыть diff</Link></td></tr>
              ))}
              {!reviews.length ? <tr><td colSpan={4}>Нет заявок на проверку</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="admin-section">
        <h2 className="admin-section-title">Места без направления</h2>
        <div className="admin-table-wrap">
          <table className="admin-table" data-testid="orphans-table">
            <thead><tr><th>ID</th><th>Название</th><th>Slug</th></tr></thead>
            <tbody>
              {orphans.map((o) => (
                <tr key={o.id}><td>{o.id}</td><td>{o.title}</td><td>{o.slug}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}

const statusLabel = (value: string) => ({
  queued: 'В очереди',
  running: 'В работе',
  succeeded: 'Успешно',
  partial_failed: 'С предупреждениями',
  failed: 'Ошибка',
  cancelled: 'Остановлен',
}[value] ?? 'Неизвестно')

const stageLabel = (value: string) => ({
  preparing: 'Подготовка',
  importing: 'Импорт',
  deduplicating: 'Дедупликация',
  enriching: 'Обогащение',
  merging: 'Слияние',
  recalculating_memberships: 'Пересчёт принадлежности',
  review_required: 'Нужна проверка',
  completed: 'Завершено',
}[value] ?? 'Неизвестный этап')

const modeLabel = (value: string) => ({
  full: 'Полный сбор',
  import_only: 'Только импорт',
  enrich_only: 'Только обогащение',
  membership_recalc_only: 'Пересчёт принадлежности',
}[value] ?? 'Неизвестный режим')

const reasonLabel = (value?: string | null) => ({
  LOW_CONFIDENCE_SCORE: 'Низкая уверенность источника',
  MANUAL_OVERRIDE_PROTECTED: 'Поле защищено ручной правкой',
  SOURCE_PRIORITY_LOWER: 'Источник ниже по приоритету',
  VALUE_CONFLICT: 'Значение отличается от текущего',
}[value ?? ''] ?? 'Требуется проверка')

const sectionLabel = (value: string) => ({
  address: 'адреса',
  photo: 'фото',
  description: 'описания',
  category: 'категории',
  coordinates: 'координаты',
  opening_hours: 'время работы',
  pending_reviews: 'заявки на проверку',
}[value] ?? value)

const scopeTypeLabel = (value: string) => ({
  catalog: 'Каталог',
  route: 'Маршруты',
  all: 'Все сценарии',
}[value] ?? 'Контур')

const assignmentLabel = (value: string) => ({
  legacy_city: 'Из города',
  imported: 'Импорт',
  manual: 'Вручную',
  spatial: 'По контуру',
  route_corridor: 'Коридор маршрута',
}[value] ?? 'Назначено')
