// Every backend status (services/route_status_service.py, see the
// canonical set in tests/route_evaluation/invariants.py::_KNOWN_STATUSES)
// must map to exactly one explicit UI state. A missing or unrecognized
// status must never be silently treated as "ready" — that was the exact
// optimistic-fallback defect: only backend-confirmed READY may ever enable
// route actions. Unknown stays unknown.
export type RouteStatusUiState = 'ready' | 'partial' | 'no_route' | 'failed' | 'preview' | 'preview_failed' | 'unknown'

export const routeStatusUiState = (status?: string | null): RouteStatusUiState => {
  switch (status) {
    case 'ready': return 'ready'
    case 'partial_route': return 'partial'
    case 'no_route': return 'no_route'
    case 'failed': return 'failed'
    case 'preview': return 'preview'
    case 'preview_failed': return 'preview_failed'
    default: return 'unknown'
  }
}

export const statusLabel = (status?: string | null) => {
  switch (routeStatusUiState(status)) {
    case 'ready': return 'Маршрут готов'
    case 'partial': return 'Маршрут частично готов'
    case 'no_route': return 'Маршрут не найден'
    case 'failed': return 'Не удалось собрать маршрут'
    case 'preview': return 'Предпросмотр маршрута'
    case 'preview_failed': return 'Не удалось собрать маршрут'
    case 'unknown': return 'Статус маршрута неизвестен'
  }
}

export const emptyTitle = (reason?: string | null) => {
  return reason === 'few_candidates_near_start' ? 'Не нашли мест поблизости' : 'Не удалось собрать маршрут'
}

export const emptyCopy = (reason?: string | null) => {
  return reason === 'few_candidates_near_start'
    ? 'Попробуй старт от центра города, другой район или более гибкое время.'
    : 'Попробуй убрать ограничения, выбрать гибкое время или открыть каталог города.'
}
