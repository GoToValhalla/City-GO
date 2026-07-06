import { buildApiUrl } from '../api/http'

export type DebugReportPayload = {
  screen: string
  severity?: 'info' | 'warning' | 'error' | 'critical'
  category?: string
  city_slug?: string | null
  destination_slug?: string | null
  place_id?: number | null
  route_id?: string | null
  request_id?: string | null
  url?: string
  environment?: string
  app_version?: string
  user_action?: string
  user_comment?: string
  title?: string
  summary?: string
  frontend_state?: Record<string, unknown>
  request_payload?: Record<string, unknown>
  response_summary?: Record<string, unknown>
  response_payload?: Record<string, unknown>
  debug_trace?: unknown
  warnings?: unknown[]
  reason_codes?: unknown[]
  browser?: Record<string, unknown>
  location_context?: Record<string, unknown>
  backend_context?: Record<string, unknown>
}

export type DebugReportResponse = {
  report_id: number
  public_id: string
  admin_url: string
  copied_summary: string
  telegram_sent: boolean
}

const SECRET_KEYS = ['authorization', 'cookie', 'token', 'secret', 'password', 'api_key']

export const buildDebugReportPayload = (payload: DebugReportPayload): DebugReportPayload => sanitize({
  severity: 'warning',
  category: 'other',
  url: window.location.href,
  browser: {
    user_agent: navigator.userAgent,
    viewport: { width: window.innerWidth, height: window.innerHeight },
    platform: navigator.platform,
    language: navigator.language,
  },
  ...payload,
}) as DebugReportPayload

export const diagnosticsSummary = (payload: DebugReportPayload): string => [
  `Screen: ${payload.screen}`,
  `City: ${payload.city_slug ?? '-'}`,
  `Request ID: ${payload.request_id ?? '-'}`,
  `URL: ${payload.url ?? window.location.href}`,
  `Status: ${payload.severity ?? 'warning'}`,
  `Warnings: ${payload.warnings?.length ?? 0}`,
  `Summary: ${payload.summary ?? '-'}`,
].join('\n')

export const sendDebugReport = async (payload: DebugReportPayload): Promise<DebugReportResponse> => {
  const response = await fetch(buildApiUrl('/debug-reports'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildDebugReportPayload(payload)),
  })
  if (!response.ok) throw new Error('Не удалось отправить отчёт')
  return response.json() as Promise<DebugReportResponse>
}

const sanitize = (value: unknown): unknown => {
  if (Array.isArray(value)) return value.map(sanitize)
  if (!value || typeof value !== 'object') return typeof value === 'string' ? stripSecrets(value) : value
  return Object.fromEntries(Object.entries(value).map(([key, item]) => [
    key,
    SECRET_KEYS.some((secret) => key.toLowerCase().includes(secret)) ? '[REDACTED]' : sanitize(item),
  ]))
}

const stripSecrets = (value: string): string => value
  .replace(/Bearer\s+[A-Za-z0-9._~+/=-]+/g, 'Bearer [REDACTED]')
  .replace(/(password|token|secret|api_key)=([^&\s]+)/gi, '$1=[REDACTED]')
