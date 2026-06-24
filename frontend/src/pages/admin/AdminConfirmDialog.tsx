import { useState } from 'react'

type Props = {
  open: boolean
  title: string
  message: string
  confirmLabel: string
  requireReason?: boolean
  busy?: boolean
  onCancel: () => void
  onConfirm: (reason: string) => void
}

export const AdminConfirmDialog = ({
  open, title, message, confirmLabel, requireReason = false, busy, onCancel, onConfirm,
}: Props) => {
  const [reason, setReason] = useState('')
  if (!open) return null
  return (
    <div className="admin-dialog-backdrop" role="presentation">
      <section className="admin-dialog" role="dialog" aria-modal="true" aria-label={title}>
        <h3>{title}</h3>
        <p>{message}</p>
        {requireReason ? (
          <label className="admin-field">
            <span>Причина</span>
            <textarea value={reason} onChange={(event) => setReason(event.target.value)} />
          </label>
        ) : null}
        <div className="admin-actions-cell">
          <button type="button" className="admin-btn" disabled={busy} onClick={onCancel}>Отмена</button>
          <button
            type="button"
            className="admin-btn admin-btn-primary"
            disabled={busy || (requireReason && !reason.trim())}
            onClick={() => onConfirm(reason.trim())}
          >
            {busy ? 'Выполняется...' : confirmLabel}
          </button>
        </div>
      </section>
    </div>
  )
}
