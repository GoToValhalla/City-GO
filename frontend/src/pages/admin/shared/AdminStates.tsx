import type { ReactNode } from 'react'

type StateProps = { message: string; children?: ReactNode }
type ErrorProps = StateProps & { title?: string; onRetry?: () => void }

export const AdminLoading = ({ message = 'Загрузка…' }: { message?: string }) => (
  <div className="admin-state" role="status">{message}</div>
)

export const AdminError = ({ message }: StateProps) => (
  <div className="admin-state admin-state-error" role="alert">{message}</div>
)

export const AdminSectionError = ({ title = 'Ошибка загрузки', message, children, onRetry }: ErrorProps) => (
  <div className="admin-state admin-state-error admin-state-section-error" role="alert">
    <strong>{title}</strong>
    <p>{message}</p>
    {children}
    {onRetry && <button type="button" className="admin-btn admin-btn-sm" onClick={onRetry}>Повторить</button>}
  </div>
)

export const AdminEmpty = ({ message, children }: StateProps) => (
  <div className="admin-state">
    <p>{message}</p>
    {children}
  </div>
)
