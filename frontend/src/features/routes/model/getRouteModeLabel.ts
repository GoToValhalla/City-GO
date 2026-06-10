// Преобразует технический режим маршрута
// в понятный текст для интерфейса.
export const getRouteModeLabel = (routeMode?: string | null) => {
  // Маршрут с общественным транспортом.
  if (routeMode === 'public_transport') {
    return 'Общественный транспорт'
  }

  // Смешанный маршрут: пешком + транспорт.
  if (routeMode === 'mixed') {
    return 'Смешанный маршрут'
  }

  // Значение по умолчанию.
  return 'Пешком'
}
