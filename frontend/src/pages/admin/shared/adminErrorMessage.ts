/** Преобразует технический ответ API в понятное сообщение на русском. */

const HTML_RE = /<\s*html|<\s*head|<title>|nginx|Bad Gateway|502/i

const STATUS_MESSAGES: Record<number, string> = {
  400: 'Некорректный запрос. Проверьте введённые данные.',
  401: 'Сессия истекла. Войдите снова.',
  403: 'Недостаточно прав для этого действия.',
  404: 'Данные не найдены.',
  422: 'Некорректные параметры запроса.',
  500: 'Внутренняя ошибка сервера.',
  502: 'Шлюз или backend временно недоступен.',
  503: 'Сервис недоступен. Проверьте настройку ADMIN_API_TOKEN на сервере.',
}

type ParsedError = { message: string | null; requestId: string | null; body: unknown }

export type AdminErrorDetails = {
  method: string
  endpoint: string
  status?: number
  statusText?: string
  raw?: string
  requestId?: string | null
}

const parseJsonDetail = (text: string): ParsedError => {
  try {
    const data = JSON.parse(text) as Record<string, unknown>
    const detail = data.detail
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail) && typeof detail[0]?.msg === 'string'
        ? detail[0].msg
        : typeof data.message === 'string'
          ? data.message
          : typeof data.error === 'string'
            ? data.error
            : null
    const requestId = typeof data.request_id === 'string' ? data.request_id : null
    return { message, requestId, body: data }
  } catch {
    return { message: null, requestId: null, body: null }
  }
}

export const toAdminErrorMessage = (status: number, raw: string): string => {
  if (HTML_RE.test(raw)) return STATUS_MESSAGES[502] ?? 'Сервер вернул техническую ошибку.'
  const jsonDetail = parseJsonDetail(raw).message
  if (jsonDetail) return jsonDetail
  if (STATUS_MESSAGES[status]) return STATUS_MESSAGES[status]
  const trimmed = raw.trim().slice(0, 200)
  return trimmed ? `Ошибка ${status}: ${trimmed}` : `Ошибка ${status}`
}

export const toAdminEndpointErrorMessage = (details: AdminErrorDetails): string => {
  const prefix = `${details.method.toUpperCase()} ${details.endpoint}`
  if (details.status == null) {
    const reason = details.raw?.trim() || 'нет ответа от сервера'
    return `Backend недоступен для ${prefix}. Причина: ${reason}`
  }
  const parsed = parseJsonDetail(details.raw ?? '')
  const requestId = details.requestId ?? parsed.requestId
  const message = toAdminErrorMessage(details.status, details.raw ?? details.statusText ?? '')
  const rid = requestId ? ` · requestId: ${requestId}` : ''
  return `${message} · ${prefix} · HTTP ${details.status}${rid}`
}
