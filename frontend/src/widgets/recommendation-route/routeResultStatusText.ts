export const statusLabel = (status?: string) => {
  if (status === 'partial_route') return 'Маршрут частично готов'
  if (status === 'no_route') return 'Маршрут не найден'
  return 'Маршрут готов'
}

export const emptyTitle = (reason?: string | null) => {
  return reason === 'few_candidates_near_start' ? 'Не нашли мест поблизости' : 'Не удалось собрать маршрут'
}

export const emptyCopy = (reason?: string | null) => {
  return reason === 'few_candidates_near_start'
    ? 'Попробуй старт от центра города, другой район или более гибкое время.'
    : 'Попробуй убрать ограничения, выбрать гибкое время или открыть каталог города.'
}
