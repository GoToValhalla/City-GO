import { useCallback, useEffect, useRef, useState } from 'react'
import type { GeoPoint } from './geo'

export type RouteGeolocationStatus = 'idle' | 'requesting' | 'granted' | 'denied' | 'unsupported' | 'unavailable'

type RouteGeolocationState = {
  status: RouteGeolocationStatus
  position: GeoPoint | null
  errorMessage: string | null
}

const errorMessage = (error: GeolocationPositionError): string => {
  if (error.code === error.PERMISSION_DENIED) return 'Доступ к геолокации запрещен в браузере.'
  if (error.code === error.POSITION_UNAVAILABLE) return 'Не удалось получить координаты устройства.'
  if (error.code === error.TIMEOUT) return 'Геолокация не ответила вовремя.'
  return error.message || 'Геолокация временно недоступна.'
}

export const useRouteGeolocation = () => {
  const [state, setState] = useState<RouteGeolocationState>({
    status: 'idle',
    position: null,
    errorMessage: null,
  })
  const watchIdRef = useRef<number | null>(null)

  const stop = useCallback(() => {
    if (watchIdRef.current != null && navigator.geolocation) {
      navigator.geolocation.clearWatch(watchIdRef.current)
    }
    watchIdRef.current = null
  }, [])

  const requestLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setState((current) => ({ ...current, status: 'unsupported', errorMessage: 'Браузер не поддерживает геолокацию.' }))
      return
    }

    setState((current) => ({ ...current, status: current.position ? 'granted' : 'requesting', errorMessage: null }))
    if (watchIdRef.current != null) return

    watchIdRef.current = navigator.geolocation.watchPosition(
      (position) => {
        setState({
          status: 'granted',
          position: {
            lat: position.coords.latitude,
            lng: position.coords.longitude,
            accuracy: position.coords.accuracy,
          },
          errorMessage: null,
        })
      },
      (error) => {
        watchIdRef.current = null
        setState((current) => ({
          ...current,
          status: error.code === error.PERMISSION_DENIED ? 'denied' : 'unavailable',
          errorMessage: errorMessage(error),
        }))
      },
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 12000 },
    )
  }, [])

  useEffect(() => stop, [stop])

  return { ...state, requestLocation, stop }
}
