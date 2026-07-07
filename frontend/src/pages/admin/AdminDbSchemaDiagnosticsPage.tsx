import { useCallback, useEffect, useState } from 'react'
import { adminGet } from './adminApi'
import { AdminLoading, AdminSectionError } from './shared/AdminStates'

type ContractDiagnostics = {
  status: 'ok' | 'schema_drift'
  missing_tables: string[]
  missing_columns: string[]
  existing_tables: string[]
  existing_columns: string[]
  extra_info: Record<string, unknown>
}

type DbSchemaDiagnostics = {
  status: 'ok' | 'schema_drift'
  alembic_version: string | null
  checked_at: string
  contracts: Record<string, ContractDiagnostics>
  raw_summary: { tables_checked: number; columns_checked: number; missing_total: number }
}

const CONTRACT_LABELS: Record<string, string> = {
  import_critical: 'Импорт',
  photo_critical: 'Фото',
  route_critical: 'Маршруты',
}

export const AdminDbSchemaDiagnosticsPage = () => {
  const [report, setReport] = useState<DbSchemaDiagnostics | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setReport(await adminGet<DbSchemaDiagnostics>('/admin/diagnostics/db-schema', { cache: false }))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось загрузить диагностику схемы')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const copyReport = async () => {
    if (!report) return
    await navigator.clipboard.writeText(JSON.stringify(report, null, 2))
    setCopied(true)
    window.setTimeout(() => setCopied(false), 2000)
  }

  if (loading) return <AdminLoading message="Проверка схемы БД…" />
  if (error) return <AdminSectionError title="Схема БД" message={error} onRetry={() => void load()} />
  if (!report) return null

  const ok = report.status === 'ok'

  return <div className="admin-page" data-testid="admin-db-schema-page">
    <header className="admin-page-header">
      <div>
        <h1 className="admin-page-title">Схема БД</h1>
        <p className="admin-page-subtitle">Read-only сравнение production-схемы с контрактами импорта, фото и маршрутов.</p>
      </div>
      <button type="button" className="admin-btn" onClick={() => void copyReport()}>Скопировать отчёт</button>
    </header>
    <section className={`admin-state ${ok ? 'admin-state-success' : 'admin-state-warning'}`}>
      <strong>{ok ? 'Схема соответствует контракту' : 'Есть расхождения'}</strong>
      <p>Alembic version: <code>{report.alembic_version ?? '—'}</code></p>
      <p>Проверено: {new Date(report.checked_at).toLocaleString('ru-RU')}</p>
      <p>Таблиц в БД: {report.raw_summary.tables_checked} · колонок в контракте: {report.raw_summary.columns_checked} · расхождений: {report.raw_summary.missing_total}</p>
      {copied ? <p className="admin-muted">Отчёт скопирован</p> : null}
    </section>
    {Object.entries(report.contracts).map(([key, contract]) => (
      <section className="admin-help-panel" key={key} data-testid={`schema-contract-${key}`}>
        <div className="admin-help-title">{CONTRACT_LABELS[key] ?? key} · {contract.status === 'ok' ? 'OK' : 'schema_drift'}</div>
        <p><strong>Критичные таблицы:</strong> {contract.existing_tables.join(', ') || '—'}</p>
        {contract.missing_tables.length > 0 ? <p className="admin-error-text"><strong>Отсутствующие таблицы:</strong> {contract.missing_tables.join(', ')}</p> : null}
        {contract.missing_columns.length > 0 ? <div className="admin-error-text" data-testid={`missing-columns-${key}`}><strong>Отсутствующие колонки:</strong><ul>{contract.missing_columns.map((column) => <li key={column}><code>{column}</code></li>)}</ul></div> : <p className="admin-muted">Отсутствующие колонки: нет</p>}
      </section>
    ))}
    <section className="admin-help-panel">
      <div className="admin-help-title">JSON отчёт</div>
      <pre data-testid="schema-json-block">{JSON.stringify(report, null, 2)}</pre>
    </section>
  </div>
}
