import { gateLabel } from './adminPublicationLabels'
import type { ReadinessGate } from './adminPlaceReadinessGates'

type Props = {
  gates: ReadinessGate[]
  title?: string
}

/** Human-readable readiness checklist (pass/fail + why). */
export const AdminReadinessBreakdown = ({ gates, title = 'Почему не готово' }: Props) => {
  if (!gates.length) return null
  const failed = gates.filter((gate) => !gate.ok)
  return (
    <section className="admin-detail-panel admin-readiness-breakdown" aria-label={title}>
      <h3>{title}</h3>
      {failed.length === 0 ? (
        <p className="admin-success-text">Все ключевые поля заполнены.</p>
      ) : (
        <p className="admin-muted">Не пройдено: {failed.length} из {gates.length}</p>
      )}
      <ul className="admin-gate-list">
        {gates.map((gate) => (
          <li key={gate.key} className={gate.ok ? 'admin-gate-ok' : 'admin-gate-fail'}>
            <strong>{gate.ok ? 'OK' : 'Нет'} · {gateLabel(gate.key)}</strong>
            <span>{gate.detail}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
