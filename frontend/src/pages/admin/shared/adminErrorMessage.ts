/** Преобразует технический ответ API в понятное сообщение на русском. */

const HTML_RE = /<\s*html|<\s*head|<title>|nginx|Bad Gateway|502/i

const STATUS_MESSAGES: Record<number, string> = {
  400: 'Некорректный запрос. Проверьте введённые данные.',
  401: 'Сессия истекла. Войдите снова.',
  403: 'Недостаточно прав для этого действия.',
  404: 'Данные не найдены.',
  422: 'Некорректные параметры запроса.',
  500: 'Внутренняя ошибка сервера. Попробуйте позже.',
  502: 'Сервер временно недоступен. Проверьте, что backend запущен.',
  503: 'Сервис недоступен. Проверьте настройку ADMIN_API_TOKEN на сервере.',
}

const parseJsonDetail = (text: string): string | null => {
  try {
    const data = JSON.parse(text) as { detail?: string | { msg?: string }[] }
    if (typeof data.detail === 'string') return data.detail
    if (Array.isArray(data.detail) && data.detail[0]?.msg) return data.detail[0].msg
  } catch {
    return null
  }
  return null
}

export const toAdminErrorMessage = (status: number, raw: string): string => {
  if (HTML_RE.test(raw)) return STATUS_MESSAGES[502] ?? 'Сервер вернул техническую ошибку.'
  const jsonDetail = parseJsonDetail(raw)
  if (jsonDetail) return jsonDetail
  if (STATUS_MESSAGES[status]) return STATUS_MESSAGES[status]
  const trimmed = raw.trim().slice(0, 200)
  return trimmed ? `Ошибка ${status}: ${trimmed}` : `Ошибка ${status}`
}
