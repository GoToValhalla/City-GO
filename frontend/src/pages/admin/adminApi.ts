import { clearAdminSession } from './adminSession'
import { requireAdminApiToken } from './adminToken'
import { toAdminErrorMessage } from './shared/adminErrorMessage'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

const handleUnauthorized = (): never => {
  clearAdminSession()
  window.location.href = '/admin/login'
  throw new Error('Unauthorised — session cleared')
}

/**
 * Единый HTTP-клиент для admin API.
 * Добавляет Authorization: Bearer <VITE_ADMIN_API_TOKEN> к каждому запросу.
 * При 401/403 разлогинивает и редиректит на /admin/login.
 */
export const adminRequest = async <T>(
  path: string,
  options: RequestInit = {},
): Promise<T> => {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${requireAdminApiToken()}`,
      ...(options.headers ?? {}),
    },
  })

  if (response.status === 401 || response.status === 403) {
    handleUnauthorized()
  }

  if (!response.ok) {
    const text = await response.text().catch(() => response.statusText)
    throw new Error(toAdminErrorMessage(response.status, text))
  }

  return response.json() as Promise<T>
}

export const adminGet = <T>(path: string) => adminRequest<T>(path)

export const adminPost = <T>(path: string, body?: unknown) =>
  adminRequest<T>(path, { method: 'POST', body: body !== undefined ? JSON.stringify(body) : undefined })

export const adminPut = <T>(path: string, body?: unknown) =>
  adminRequest<T>(path, { method: 'PUT', body: body !== undefined ? JSON.stringify(body) : undefined })

export const adminPatch = <T>(path: string, body?: unknown) =>
  adminRequest<T>(path, { method: 'PATCH', body: body !== undefined ? JSON.stringify(body) : undefined })
