import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminGet, adminPostLong } from './adminApi'
import type { AdminCitiesResponse } from './adminTypes'
import { AdminError, AdminLoading } from './shared/AdminStates'
import './AdminAIPage.css'

type AdminAITask = {
  id: string
  label: string
  description: string
  result_mode: string
  risk_level: string
  enabled: boolean
}

type AdminAIModelOption = {
  value: string
  label: string
  model: string
  description: string
}

type AdminAITasksResponse = {
  tasks: AdminAITask[]
  model_options: AdminAIModelOption[]
  default_task_id: string
  default_model_mode: string
}

type AdminAIResultItem = {
  place_id: number | null
  title: string
  summary: string
  recommended_action: string
  confidence: number | null
}

type AdminAIResult = {
  task_id: string
  task_label: string
  city_slug: string
  model: string
  status: string
  rows_processed: number
  rows_updated: number
  applied: boolean
  batch_id: string | null
  items: AdminAIResultItem[]
  errors: string[]
  message: string
  next_action: string
}

const LIMIT_OPTIONS = [5, 10, 20, 50]
const LAST_AI_RESULT_STORAGE_KEY = 'citygo.admin.ai.lastResult'

const readStoredAIResult = (): AdminAIResult | null => {
  try {
    const raw = window.sessionStorage.getItem(LAST_AI_RESULT_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as AdminAIResult
    return parsed && typeof parsed === 'object' && typeof parsed.task_id === 'string' ? parsed : null
  } catch {
    return null
  }
}

const writeStoredAIResult = (result: AdminAIResult | null) => {
  try {
    if (result) {
      window.sessionStorage.setItem(LAST_AI_RESULT_STORAGE_KEY, JSON.stringify(result))
    } else {
      window.sessionStorage.removeItem(LAST_AI_RESULT_STORAGE_KEY)
    }
  } catch {
    // Ignore storage errors: the current in-memory result is still shown.
  }
}

const resultModeLabel = (task: AdminAITask) => (
  task.result_mode === 'auto_apply'
    ? 'подготовит изменения и покажет результат'
    : 'только отчёт и ручная проверка'
)

export const AdminAIPage = () => {
  const [tasks, setTasks] = useState<AdminAITask[]>([])
  const [models, setModels] = useState<AdminAIModelOption[]>([])
  const [cities, setCities] = useState<AdminCitiesResponse['items']>([])
  const [taskId, setTaskId] = useState('')
  const [citySlug, setCitySlug] = useState('')
  const [modelMode, setModelMode] = useState('economy')
  const [limit, setLimit] = useState(10)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<AdminAIResult | null>(() => readStoredAIResult())

  const selectedTask = useMemo(() => tasks.find((task) => task.id === taskId) ?? null, [tasks, taskId])
  const selectedModel = useMemo(() => models.find((model) => model.value === modelMode) ?? null, [models, modelMode])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [ai, cityResponse] = await Promise.all([
        adminGet<AdminAITasksResponse>('/admin/ai/tasks'),
        adminGet<AdminCitiesResponse>('/admin/cities?limit=100'),
      ])
      const storedResult = readStoredAIResult()
      setTasks(ai.tasks)
      setModels(ai.model_options)
      setTaskId((current) => current || storedResult?.task_id || ai.default_task_id)
      setModelMode(ai.default_model_mode)
      setCities(cityResponse.items)
      setCitySlug((current) => current || storedResult?.city_slug || cityResponse.items[0]?.slug || '')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось загрузить AI-раздел')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const run = async () => {
    if (!selectedTask || !citySlug) return
    const ok = window.confirm(`${selectedTask.label}: ${citySlug}, ${limit} мест, ${selectedModel?.label ?? modelMode}?`)
    if (!ok) return
    setRunning(true)
    setError(null)
    setResult(null)
    writeStoredAIResult(null)
    try {
      const response = await adminPostLong<AdminAIResult>('/admin/ai/run', {
        task_id: selectedTask.id,
        city_slug: citySlug,
        model_mode: modelMode,
        limit,
        apply_safe_changes: true,
      })
      setResult(response)
      writeStoredAIResult(response)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'AI-задача завершилась ошибкой')
    } finally {
      setRunning(false)
    }
  }

  if (loading) return <AdminLoading />

  return <div>
    <h2 className="admin-page-title">AI</h2>
    <p className="admin-page-subtitle">Выберите задачу, город и лимит. Результат останется на экране после перехода в карточки.</p>
    {error && <AdminError message={error} />}
    <section className="admin-action-grid admin-ai-task-grid" style={{ marginTop: 16 }}>
      {tasks.map((task) => <button key={task.id} type="button" disabled={!task.enabled || running} className={`admin-action-card admin-ai-task-card ${taskId === task.id ? 'admin-row-highlight' : ''}`} onClick={() => setTaskId(task.id)}>
        <strong>{task.label}</strong>
        <span className="admin-muted">{task.description}</span>
        <span className={`admin-badge ${task.risk_level === 'safe' ? 'pub-published' : 'pub-needs_review'}`}>{resultModeLabel(task)}</span>
      </button>)}
    </section>
    <section className="admin-filter-card admin-ai-settings-card" style={{ marginTop: 16 }}>
      <div className="admin-help-title">Минимальные настройки</div>
      <div className="admin-filter-grid admin-ai-settings-grid">
        <label className="admin-field">Город<select value={citySlug} onChange={(e) => setCitySlug(e.target.value)}>{cities.map((city) => <option key={city.slug} value={city.slug}>{city.name}</option>)}</select></label>
        <label className="admin-field">Модель<select value={modelMode} onChange={(e) => setModelMode(e.target.value)}>{models.map((model) => <option key={model.value} value={model.value}>{model.label} · {model.model}</option>)}</select></label>
        <label className="admin-field">Лимит<select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>{LIMIT_OPTIONS.map((value) => <option key={value} value={value}>{value} мест</option>)}</select></label>
      </div>
      {selectedModel && <p className="admin-muted" style={{ marginTop: 10 }}>{selectedModel.description}</p>}
      <div className="admin-actions-cell admin-ai-primary-actions" style={{ marginTop: 14 }}>
        <button type="button" className="admin-btn admin-btn-primary" disabled={running || !selectedTask || !citySlug} onClick={() => void run()}>{running ? 'AI работает…' : 'Запустить'}</button>
        {citySlug && <Link className="admin-btn" to={`/admin/places?city=${citySlug}`}>Открыть места города</Link>}
      </div>
    </section>
    {result && <section className="admin-detail-panel admin-ai-result-panel">
      <h3>{result.task_label}</h3>
      <p>{result.message}</p>
      <div className="admin-metrics-grid admin-metrics-small admin-ai-metrics">
        <div className="admin-metric-card"><div className="admin-metric-value">{result.rows_processed}</div><div className="admin-metric-label">обработано</div></div>
        <div className="admin-metric-card"><div className="admin-metric-value">{result.rows_updated}</div><div className="admin-metric-label">изменено</div></div>
        <div className="admin-metric-card"><div className="admin-metric-value">{result.applied ? 'Да' : 'Нет'}</div><div className="admin-metric-label">применено</div></div>
        <div className="admin-metric-card"><div className="admin-metric-value">{result.errors.length}</div><div className="admin-metric-label">ошибок</div></div>
      </div>
      <p className="admin-muted">Следующий шаг: {result.next_action}</p>
      {result.errors.length > 0 && <div className="admin-state admin-state-error">{result.errors.join('; ')}</div>}
      {result.items.length > 0 && <div className="admin-ai-result-list">
        {result.items.map((item) => <article className="admin-ai-result-card" key={`${item.place_id}-${item.title}`}>
          <div className="admin-ai-result-place">
            {item.place_id ? <Link to={`/admin/places/${item.place_id}`}>{item.title}</Link> : item.title}
            {item.confidence != null && <span>{Math.round(item.confidence * 100)}%</span>}
          </div>
          <div className="admin-ai-result-body">
            <p>{item.summary}</p>
            <small>{item.recommended_action}</small>
          </div>
        </article>)}
      </div>}
      <div className="admin-actions-cell admin-ai-primary-actions" style={{ marginTop: 14 }}>
        <Link className="admin-btn admin-btn-sm" to={`/admin/places?city=${result.city_slug}`}>Открыть места</Link>
        <Link className="admin-btn admin-btn-sm" to={`/admin/audit?action=admin_ai_run&entity_id=${result.task_id}`}>Открыть аудит</Link>
      </div>
    </section>}
  </div>
}
