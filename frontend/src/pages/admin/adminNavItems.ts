export type AdminNavItem = { path: string; label: string; section?: string }

export const ADMIN_NAV_ITEMS: AdminNavItem[] = [
  { path: '/admin/overview', label: 'Обзор', section: 'main' },
  { path: '/admin/cities', label: 'Города', section: 'main' },
  { path: '/admin/places', label: 'Места', section: 'data' },
  { path: '/admin/coverage', label: 'Покрытие данных', section: 'data' },
  { path: '/admin/routes/eligibility', label: 'Маршруты → Eligibility', section: 'data' },
  { path: '/admin/routes/dry-run', label: 'Маршруты → Dry Run', section: 'data' },
  { path: '/admin/routes/data-quality', label: 'Маршруты → Data Quality', section: 'data' },
  { path: '/admin/photos', label: 'Фото', section: 'moderation' },
  { path: '/admin/verification', label: 'Верификация', section: 'moderation' },
  { path: '/admin/imports', label: 'Импорты', section: 'ops' },
  { path: '/admin/enrichment', label: 'Обогащение данных', section: 'ops' },
  { path: '/admin/features', label: 'Фичи и настройки', section: 'system' },
  { path: '/admin/metrics', label: 'Метрики', section: 'system' },
  { path: '/admin/audit', label: 'Журнал аудита', section: 'system' },
  { path: '/admin/system-logs', label: 'Системные логи', section: 'system' },
]
