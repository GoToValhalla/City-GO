import { useCallback, useState } from 'react'
import type { MapCoordinate } from '../map/yandexMaps'

type LocationStatus = 'idle' | 'loading' | 'granted' | 'denied' | 'unsupported' | 'error'

export type UserLocationState = {
  status: LocationStatus
  coordinates: MapCoordinate | null
  error: string | null
  requestLocation: () => void
}

const isLocalhost = () => ['localhost', '127.0.0.1', '::1'].includes(window.location.hostname)

export const useUserLocation = (): UserLocationState => {
  const [status, setStatus] = useState<LocationStatus>('idle')
  const [coordinates, setCoordinates] = useState<MapCoordinate | null>(null)
  const [error, setError] = useState<string | null>(null)

  const requestLocation = useCallback(() => {
    setError(null)

    if (!('geolocation' in navigator)) {
      setStatus('unsupported')
      setError('Геопозиция не поддерживается на этом устройстве.')
      return
    }

    if (!window.isSecureContext && !isLocalhost()) {
      setStatus('denied')
      setError('Геопозиция работает только через HTTPS или localhost.')
      return
    }

    setStatus('loading')
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setCoordinates({ lat: position.coords.latitude, lng: position.coords.longitude })
        setStatus('granted')
      },
      (geoError) => {
        setStatus(geoError.code === geoError.PERMISSION_DENIED ? 'denied' : 'error')
        setError(geoError.code === geoError.PERMISSION_DENIED ? 'Доступ к геопозиции не разрешён.' : 'Не удалось определить геопозицию.')
      },
      {
        enableHighAccuracy: true,
        maximumAge: 60_000,
        timeout: 10_000,
      },
    )
  }, [])

  return { status, coordinates, error, requestLocation }
}
