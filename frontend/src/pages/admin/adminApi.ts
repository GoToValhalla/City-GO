import { clearAdminSession } from './adminSession'
import { requireAdminApiToken } from './adminToken'
import { toAdminErrorMessage } from './shared/adminErrorMessage'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
const ADMIN_REQUEST_TIMEOUT_MS = 15_000

const handleUnauthorized = (): never => {
  clearAdminSession()
  window.location.href = '/admin/login'
  throw new Error('Сессия администратора завершена')
}

const timeoutMessage = 'Сервер не ответил за 15 секунд. Проверьте состояние базы данных и повторите запрос.'

/**
 * Единый HTTP-клиент для admin API.
 * Каждый запрос ограничен по времени, чтобы отказ БД не оставлял экран в вечной загрузке.
 */
export const adminRequest = async <T>(
  path: string,
  options: RequestInit = {},
): Promise<T> => {
  const timeoutController = new AbortController()
  const timeoutId = window.setTimeout(() => timeoutController.abort(), ADMIN_REQUEST_TIMEOUT_MS)
  const externalSignal = options.signal
  const abortFromExternalSignal = () => timeoutController.abort()
  externalSignal?.addEventListener('abort', abortFromExternalSignal, { once: true })

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: timeoutController.signal,
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
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      if (externalSignal?.aborted) throw error
      throw new Error(timeoutMessage)
    }
    throw error
  } finally {
    window.clearTimeout(timeoutId)
    externalSignal?.removeEventListener('abort', abortFromExternalSignal)
  }
}

export const adminGet = <T>(path: string) => adminRequest<T>(path)

export const adminPost = <T>(path: string, body?: unknown) =>
  adminRequest<T>(path, { method: 'POST', body: body !== undefined ? JSON.stringify(body) : undefined })

export const adminPut = <T>(path: string, body?: unknown) =>
  adminRequest<T>(path, { method: 'PUT', body: body !== undefined ? JSON.stringify(body) : undefined })

export const adminPatch = <T>(path: string, body?: unknown) =>
  adminRequest<T>(path, { method: 'PATCH', body: body !== undefined ? JSON.stringify(body) : undefined })