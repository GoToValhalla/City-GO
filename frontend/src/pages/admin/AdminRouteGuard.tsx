import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { hasAdminSession } from './adminSession'

type Props = { children: ReactNode }

/**
 * Защищает admin-маршруты: без активной сессии редиректит на /admin/login.
 */
export const AdminRouteGuard = ({ children }: Props) => {
  if (!hasAdminSession()) {
    return <Navigate to="/admin/login" replace />
  }
  return <>{children}</>
}
