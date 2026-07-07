export type AdminNavItem = { path: string; label: string; section?: string }

export const ADMIN_NAV_ITEMS: AdminNavItem[] = [
  { path: '/admin/overview', label: 'Обзор', section: 'main' },
  { path: '/admin/cities', label: 'Города', section: 'main' },
  { path: '/admin/ai', label: 'AI', section: 'main' },
  { path: '/admin/places', label: 'Места', section: 'data' },
  { path: '/admin/taxonomy', label: 'Таксономия', section: 'data' },
  { path: '/admin/coverage', label: 'Покрытие данных', section: 'data' },
  { path: '/admin/coverage?tab=gaps', label: 'Пропущенные must-have', section: 'data' },
  { path: '/admin/quality', label: 'Качество', section: 'data' },
  { path: '/admin/routes/eligibility', label: 'Маршруты: готовность мест', section: 'routes' },
  { path: '/admin/routes/dry-run', label: 'Маршруты: проверка сборки', section: 'routes' },
  { path: '/admin/routes/data-quality', label: 'Маршруты: качество данных', section: 'routes' },
  { path: '/admin/route-health', label: 'Маршруты: диагностика', section: 'routes' },
  { path: '/admin/photos', label: 'Фото', section: 'moderation' },
  { path: '/admin/verification', label: 'Проверка мест', section: 'moderation' },
  { path: '/admin/place-changes', label: 'Изменения мест', section: 'moderation' },
  { path: '/admin/reviews', label: 'Слияние данных', section: 'moderation' },
  { path: '/admin/data-pipeline', label: 'Мониторинг конвейера данных', section: 'ops' },
  { path: '/admin/discovery', label: 'Открытие направлений', section: 'ops' },
  { path: '/admin/destinations', label: 'Направления', section: 'ops' },
  { path: '/admin/imports', label: 'Импорты', section: 'ops' },
  { path: '/admin/enrichment', label: 'Обогащение данных', section: 'ops' },
  { path: '/admin/features', label: 'Фичи и настройки', section: 'system' },
  { path: '/admin/metrics', label: 'Метрики', section: 'system' },
  { path: '/admin/analytics', label: 'Аналитика', section: 'system' },
  { path: '/admin/system-health', label: 'Состояние системы', section: 'system' },
  { path: '/admin/diagnostics/db-schema', label: 'Схема БД', section: 'system' },
  { path: '/admin/debug-reports', label: 'Отчёты об ошибках', section: 'system' },
  { path: '/admin/audit', label: 'Журнал действий', section: 'system' },
  { path: '/admin/system-logs', label: 'Системные логи', section: 'system' },
]

export const ADMIN_NAV_SECTION_LABELS: Record<string, string> = {
  main: 'Главное', data: 'Каталог', routes: 'Маршруты', moderation: 'Проверка', ops: 'Операции', system: 'Система',
}
