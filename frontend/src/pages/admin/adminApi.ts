import { clearAdminSession } from './adminSession'
import { requireAdminApiToken } from './adminToken'
import { toAdminEndpointErrorMessage } from './shared/adminErrorMessage'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
const ADMIN_REQUEST_TIMEOUT_MS = 8_000
const ADMIN_LONG_REQUEST_TIMEOUT_MS = 600_000
const ADMIN_GET_CACHE_TTL_MS = 0
const ADMIN_GET_CACHE_MAX_ENTRIES = 0
const ADMIN_GET_CACHE_ENABLED = false

type AdminRequestOptions = RequestInit & { timeoutMs?: number }
type AdminGetOptions = { cache?: boolean; timeoutMs?: number }
type AdminWriteOptions = { invalidateCache?: boolean; timeoutMs?: number }
type AdminGetCacheEntry = {
  expiresAt: number
  data?: unknown
  hasData?: boolean
  promise?: Promise<unknown>
}

const adminGetCache = new Map<string, AdminGetCacheEntry>()

export class AdminApiError extends Error {
  method: string
  endpoint: string
  status?: number
  statusText?: string
  responseText?: string
  requestId?: string | null
  cause?: unknown

  constructor(details: {
    method: string
    endpoint: string
    status?: number
    statusText?: string
    responseText?: string
    requestId?: string | null
    cause?: unknown
  }) {
    super(toAdminEndpointErrorMessage({
      method: details.method,
      endpoint: details.endpoint,
      status: details.status,
      statusText: details.statusText,
      raw: details.responseText,
      requestId: details.requestId,
    }))
    this.name = 'AdminApiError'
    this.method = details.method
    this.endpoint = details.endpoint
    this.status = details.status
    this.statusText = details.statusText
    this.responseText = details.responseText
    this.requestId = details.requestId
    this.cause = details.cause
  }
}

const clearExpiredAdminGetCache = () => {
  const now = Date.now()
  for (const [key, entry] of adminGetCache.entries()) {
    if (entry.expiresAt <= now) adminGetCache.delete(key)
  }
}

export const clearAdminGetCache = () => adminGetCache.clear()

const rememberAdminGet = <T>(path: string, promise: Promise<T>): Promise<T> => {
  clearExpiredAdminGetCache()
  if (adminGetCache.size >= ADMIN_GET_CACHE_MAX_ENTRIES) {
    const firstKey = adminGetCache.keys().next().value
    if (firstKey) adminGetCache.delete(firstKey)
  }
  adminGetCache.set(path, { expiresAt: Date.now() + ADMIN_GET_CACHE_TTL_MS, promise })
  return promise.then((data) => {
    adminGetCache.set(path, {
      data,
      hasData: true,
      expiresAt: Date.now() + ADMIN_GET_CACHE_TTL_MS,
    })
    return data
  }).catch((error) => {
    adminGetCache.delete(path)
    throw error
  })
}

const invalidateAdminGetCache = (options: AdminWriteOptions = {}) => {
  if (options.invalidateCache !== false) clearAdminGetCache()
}

const handleUnauthorized = (): never => {
  clearAdminSession()
  window.location.href = '/admin/login'
  throw new Error('Сессия администратора завершена')
}

const timeoutMessage = (timeoutMs: number) => `Backend не ответил за ${Math.round(timeoutMs / 1000)} секунд. Экран остановлен вместо вечной загрузки. Проверьте API/БД и повторите запрос.`

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
  const method = (requestOptions.method ?? 'GET').toString().toUpperCase()

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
      throw new AdminApiError({
        method,
        endpoint: path,
        status: response.status,
        statusText: response.statusText,
        responseText: text,
        requestId: response.headers.get('x-request-id'),
      })
    }

    return response.json() as Promise<T>
  } catch (error) {
    if (error instanceof AdminApiError) {
      console.error('Admin API error', error)
      throw error
    }
    if (error instanceof DOMException && error.name === 'AbortError') {
      if (externalSignal?.aborted) throw error
      const timeoutError = new AdminApiError({ method, endpoint: path, responseText: timeoutMessage(timeoutMs), cause: error })
      console.error('Admin API timeout', timeoutError)
      throw timeoutError
    }
    if (error instanceof TypeError) {
      const networkError = new AdminApiError({ method, endpoint: path, responseText: error.message, cause: error })
      console.error('Admin API network error', networkError)
      throw networkError
    }
    throw error
  } finally {
    window.clearTimeout(timeoutId)
    externalSignal?.removeEventListener('abort', abortFromExternalSignal)
  }
}

export const adminGet = <T>(path: string, options: AdminGetOptions = {}) => {
  const request = adminRequest<T>(path, { timeoutMs: options.timeoutMs })
  if (!ADMIN_GET_CACHE_ENABLED || options.cache === false) return request
  clearExpiredAdminGetCache()
  const cached = adminGetCache.get(path)
  if (cached && cached.expiresAt > Date.now()) {
    if (cached.hasData) return Promise.resolve(cached.data as T)
    if (cached.promise) return cached.promise as Promise<T>
  }
  return rememberAdminGet(path, request)
}

export const adminPost = <T>(path: string, body?: unknown, options: AdminWriteOptions = {}) => {
  invalidateAdminGetCache(options)
  return adminRequest<T>(path, { method: 'POST', body: body !== undefined ? JSON.stringify(body) : undefined, timeoutMs: options.timeoutMs })
}

export const adminPostLong = <T>(path: string, body?: unknown, options: AdminWriteOptions = {}) => {
  invalidateAdminGetCache(options)
  return adminRequest<T>(path, {
    method: 'POST',
    body: body !== undefined ? JSON.stringify(body) : undefined,
    timeoutMs: options.timeoutMs ?? ADMIN_LONG_REQUEST_TIMEOUT_MS,
  })
}

export const adminPut = <T>(path: string, body?: unknown, options: AdminWriteOptions = {}) => {
  invalidateAdminGetCache(options)
  return adminRequest<T>(path, { method: 'PUT', body: body !== undefined ? JSON.stringify(body) : undefined, timeoutMs: options.timeoutMs })
}

export const adminPatch = <T>(path: string, body?: unknown, options: AdminWriteOptions = {}) => {
  invalidateAdminGetCache(options)
  return adminRequest<T>(path, { method: 'PATCH', body: body !== undefined ? JSON.stringify(body) : undefined, timeoutMs: options.timeoutMs })
}

export const adminDelete = <T>(path: string, options: AdminWriteOptions = {}) => {
  invalidateAdminGetCache(options)
  return adminRequest<T>(path, { method: 'DELETE', timeoutMs: options.timeoutMs })
}
