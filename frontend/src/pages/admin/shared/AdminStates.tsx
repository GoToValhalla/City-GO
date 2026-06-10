import type { ReactNode } from 'react'

type StateProps = { message: string; children?: ReactNode }

export const AdminLoading = ({ message = 'Загрузка…' }: { message?: string }) => (
  <div className="admin-state" role="status">{message}</div>
)

export const AdminError = ({ message }: StateProps) => (
  <div className="admin-state admin-state-error" role="alert">{message}</div>
)

export const AdminEmpty = ({ message, children }: StateProps) => (
  <div className="admin-state">
    <p>{message}</p>
    {children}
  </div>
)
