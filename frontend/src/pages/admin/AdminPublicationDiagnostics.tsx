import { Link } from 'react-router-dom'
import { blockerLabel, primaryBlockerSentence } from './adminPublicationLabels'
import { readinessStatusText } from './adminHumanText'

export type PublicationDiagnosticsProps = {
  title?: string
  readinessStatus?: string | null
  readinessScore?: number | null
  primaryBlocker?: string | null
  blockers?: Record<string, number> | null
  qualityScore?: number | null
  trustScore?: number | null
  reviewBlockers?: string[]
  failedGateLabels?: string[]
  snapshotWarning?: { code?: string; message?: string } | null
  snapshotVersionLabel?: string | null
  snapshotFreshnessLabel?: string | null
  blockerLinks?: Record<string, string>
}

/** Structured publication / readiness diagnostics for admin screens. */
export const AdminPublicationDiagnostics = (props: PublicationDiagnosticsProps) => {
  const {
    title = 'Диагностика публикации',
    readinessStatus,
    readinessScore,
    primaryBlocker,
    blockers,
    qualityScore,
    trustScore,
    reviewBlockers = [],
    failedGateLabels = [],
    snapshotWarning,
    snapshotVersionLabel,
    snapshotFreshnessLabel,
    blockerLinks = {},
  } = props

  const primary = primaryBlockerSentence(primaryBlocker, blockers)
  const blockerEntries = Object.entries(blockers ?? {}).filter(([, count]) => Number(count) > 0)

  return (
    <section className="admin-detail-panel admin-publication-diagnostics" aria-label={title}>
      <h3>{title}</h3>
      <div className="admin-status-strip">
        {readinessScore != null && <span className="admin-badge">Готовность {readinessScore}%</span>}
        {readinessStatus && (
          <span className="admin-badge">
            {primary ? primary : readinessStatusText(readinessStatus)}
          </span>
        )}
        {qualityScore != null && <span className="admin-badge">Качество {qualityScore}%</span>}
        {trustScore != null && <span className="admin-badge">Доверие {trustScore}%</span>}
      </div>
      {failedGateLabels.length > 0 && (
        <p><strong>Не пройденные проверки:</strong> {failedGateLabels.join(', ')}</p>
      )}
      {blockerEntries.length > 0 && (
        <ul className="admin-gate-list">
          {blockerEntries.map(([key, count]) => {
            const label = `${blockerLabel(key)}: ${count}`
            const to = blockerLinks[key]
            return (
              <li key={key} className="admin-gate-fail">
                {to ? <Link to={to}>{label} →</Link> : <span>{label}</span>}
              </li>
            )
          })}
        </ul>
      )}
      {reviewBlockers.length > 0 && (
        <p><strong>Блокеры проверки:</strong> {reviewBlockers.join('; ')}</p>
      )}
      <p className="admin-muted">
        Версия снимка: {snapshotVersionLabel ?? 'нет в ответе API'}
        {snapshotFreshnessLabel ? ` · Актуальность: ${snapshotFreshnessLabel}` : ''}
      </p>
      {snapshotWarning && (
        <p className="admin-state-warning">
          Снимок: {snapshotWarning.message ?? snapshotWarning.code ?? 'предупреждение'}
        </p>
      )}
    </section>
  )
}
