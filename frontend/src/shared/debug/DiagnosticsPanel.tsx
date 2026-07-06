import { useState } from 'react'
import { diagnosticsSummary, sendDebugReport, type DebugReportPayload } from './debugReports'
import { useDebugMode } from './useDebugMode'

type Props = {
  payload: DebugReportPayload
  details?: unknown
  compact?: boolean
}

export const DiagnosticsPanel = ({ compact = false, details, payload }: Props) => {
  const { enabled } = useDebugMode()
  const [status, setStatus] = useState<string | null>(null)
  const summary = diagnosticsSummary(payload)

  const copy = async () => {
    await navigator.clipboard?.writeText(summary)
    setStatus('Диагностика скопирована')
  }

  const send = async () => {
    setStatus('Отправляю отчёт…')
    try {
      const result = await sendDebugReport(payload)
      setStatus(`Отчёт создан: ${result.public_id}${result.telegram_sent ? ' · отправлено в Telegram' : ''}`)
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Не удалось отправить отчёт')
    }
  }

  return (
    <aside className={compact ? 'debug-panel debug-panel-compact' : 'debug-panel'}>
      {enabled ? <div className="debug-badge">DEBUG {payload.request_id ? <span>{payload.request_id}</span> : null}{payload.warnings?.length ? <strong>{payload.warnings.length}</strong> : null}</div> : null}
      <div className="debug-actions">
        <button type="button" onClick={() => void send()}>{enabled ? 'Отправить отчёт' : 'Сообщить о проблеме'}</button>
        {enabled ? <button type="button" onClick={() => void copy()}>Скопировать диагностику</button> : null}
      </div>
      {status ? <p className="debug-status">{status}</p> : null}
      {enabled ? <details className="debug-details"><summary>Техническая диагностика</summary><pre>{JSON.stringify(details ?? payload, null, 2)}</pre></details> : null}
    </aside>
  )
}
