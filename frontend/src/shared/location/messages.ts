import type { LocationState, LocationStatus } from './types'

const MESSAGES: Record<LocationStatus, string> = {
  denied: 'Разрешите доступ к геопозиции',
  error: 'Не удалось определить местоположение',
  granted: 'Местоположение определено',
  idle: 'Геопозиция не запрашивалась',
  initializing: 'Подготавливаем геопозицию',
  insecure: 'Геопозиция работает через HTTPS',
  requesting: 'Определяем местоположение',
  timeout: 'Не удалось определить местоположение за отведённое время',
  unavailable: 'Геопозиция сейчас недоступна',
}

export const locationState = (
  status: LocationStatus,
  permissionState: LocationState['permissionState'] = 'unknown',
  message = MESSAGES[status],
): LocationState => ({
  status,
  snapshot: null,
  permissionState,
  retryable: ['denied', 'error', 'timeout', 'unavailable'].includes(status),
  message,
})

export const browserErrorState = (error: GeolocationPositionError): LocationState => {
  if (error.code === error.PERMISSION_DENIED) return locationState('denied', 'denied')
  if (error.code === error.TIMEOUT) return locationState('timeout')
  if (error.code === error.POSITION_UNAVAILABLE) return locationState('unavailable')
  return locationState('error')
}
