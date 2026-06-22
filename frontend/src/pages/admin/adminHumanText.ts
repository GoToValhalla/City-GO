const PUBLICATION_STATUS_LABELS: Record<string, string> = {
  published: 'Опубликовано',
  draft: 'Черновик',
  hidden: 'Скрыто',
  unpublished: 'Снято с публикации',
  needs_review: 'На проверке',
  rejected: 'Отклонено',
}

const VERIFICATION_STATUS_LABELS: Record<string, string> = {
  verified: 'Проверено',
  unverified: 'Не проверено',
  needs_recheck: 'Нужна перепроверка',
  rejected: 'Отклонено',
  pending: 'На проверке',
}

const READINESS_STATUS_LABELS: Record<string, string> = {
  ready: 'готово',
  needs_review: 'нужно проверить',
  not_ready: 'не готово',
  failed: 'ошибка',
}

const ENTITY_LABELS: Record<string, string> = {
  place: 'место',
  city: 'город',
  route: 'маршрут',
  feature_toggle: 'настройка',
  place_image: 'фото места',
}

const LOG_LEVEL_LABELS: Record<string, string> = {
  info: 'информация',
  warning: 'предупреждение',
  error: 'ошибка',
  critical: 'критично',
}

const BULK_ACTION_LABELS: Record<string, string> = {
  send_review: 'Отправить на проверку',
  enable_route: 'Подтвердить для маршрутов',
  disable_route: 'Исключить из маршрутов',
  refresh_addresses: 'Обновить адреса',
  set_category: 'Сменить категорию',
}

const BULK_ACTION_HINTS: Record<string, string> = {
  send_review: 'Поставит выбранные места в очередь проверки качества. Публикацию само по себе не включает.',
  enable_route: 'Разрешит выбранным местам попадать в автоматические маршруты, если остальные данные в порядке.',
  disable_route: 'Запретит выбранным местам попадать в маршруты. В каталоге место может остаться опубликованным.',
  refresh_addresses: 'Поставит задачу обновления адресов для выбранных мест. Координаты и публикацию не меняет.',
  set_category: 'Перезапишет категорию выбранных мест и синхронизирует canonical_category для следующих quality gates.',
}

export const humanizeCode = (code: string | null | undefined) => {
  if (!code) return '—'
  return code.replace(/[_-]+/g, ' ')
}

export const publicationStatusText = (status: string | null | undefined) => (
  status ? PUBLICATION_STATUS_LABELS[status] ?? humanizeCode(status) : '—'
)

export const verificationStatusText = (status: string | null | undefined) => (
  status ? VERIFICATION_STATUS_LABELS[status] ?? humanizeCode(status) : '—'
)

export const readinessStatusText = (status: string | null | undefined) => (
  status ? READINESS_STATUS_LABELS[status] ?? humanizeCode(status) : '—'
)

export const entityText = (entity: string | null | undefined) => (
  entity ? ENTITY_LABELS[entity] ?? humanizeCode(entity) : '—'
)

export const logLevelText = (level: string | null | undefined) => (
  level ? LOG_LEVEL_LABELS[level] ?? humanizeCode(level) : '—'
)

export const bulkActionText = (action: string) => BULK_ACTION_LABELS[action] ?? humanizeCode(action)
export const bulkActionHint = (action: string) => BULK_ACTION_HINTS[action] ?? 'Действие изменит выбранные места.'
