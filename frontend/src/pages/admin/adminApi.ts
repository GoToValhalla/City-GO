import { clearAdminSession } from './adminSession'
import { requireAdminApiToken } from './adminToken'
import { toAdminErrorMessage } from './shared/adminErrorMessage'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
const ADMIN_REQUEST_TIMEOUT_MS = 15_000
const ADMIN_LONG_REQUEST_TIMEOUT_MS = 600_000

type AdminRequestOptions = RequestInit & { timeoutMs?: number }

const handleUnauthorized = (): never => {
  clearAdminSession()
  window.location.href = '/admin/login'
  throw new Error('Сессия администратора завершена')
}

const timeoutMessage = (timeoutMs: number) => `Сервер не ответил за ${Math.round(timeoutMs / 1000)} секунд. Проверьте состояние базы данных и повторите запрос.`

/**
 * Единый HTTP-клиент для admin API.
 * Каждый запрос ограничен по времени, чтобы отказ БД не оставлял экран в вечной загрузке.
 */
export const adminRequest = async <T>(
  path: string,
  options: AdminRequestOptions = {},
): Promise<T> => {
  const { timeoutMs = ADMIN_REQUEST_TIMEOUT_MS, ...requestOptions } = options
  const timeoutController = new AbortController()
  const timeoutId = window.setTimeout(() => timeoutController.abort(), timeoutMs)
  const externalSignal = requestOptions.signal
  const abortFromExternalSignal = () => timeoutController.abort()
  externalSignal?.addEventListener('abort', abortFromExternalSignal, { once: true })

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...requestOptions,
      signal: timeoutController.signal,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${requireAdminApiToken()}`,
        ...(requestOptions.headers ?? {}),
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
      throw new Error(timeoutMessage(timeoutMs))
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

export const adminPostLong = <T>(path: string, body?: unknown) =>
  adminRequest<T>(path, {
    method: 'POST',
    body: body !== undefined ? JSON.stringify(body) : undefined,
    timeoutMs: ADMIN_LONG_REQUEST_TIMEOUT_MS,
  })

export const adminPut = <T>(path: string, body?: unknown) =>
  adminRequest<T>(path, { method: 'PUT', body: body !== undefined ? JSON.stringify(body) : undefined })

export const adminPatch = <T>(path: string, body?: unknown) =>
  adminRequest<T>(path, { method: 'PATCH', body: body !== undefined ? JSON.stringify(body) : undefined })