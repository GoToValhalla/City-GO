import { useCallback, useEffect, useRef, useState } from 'react'
import { requestBrowserLocation, startBrowserWatch, stopBrowserWatch } from './browserProvider'
import { locationState } from './messages'
import { createSnapshot, validCoordinate } from './snapshot'
import { clearLocationSnapshot, restoreLocationSnapshot, saveLocationSnapshot } from './storage'
import { openTelegramLocationSettings, requestTelegramLocation } from './telegramProvider'
import type { LocationPoint, LocationRequest, LocationSnapshot, LocationState, LocationSource } from './types'

const initialState = (): LocationState => {
  const snapshot = restoreLocationSnapshot()
  return snapshot
    ? { status: 'granted', snapshot, permissionState: 'unknown', retryable: true, message: 'Местоположение восстановлено' }
    : locationState('idle')
}

const isSnapshot = (value: LocationSnapshot | LocationState): value is LocationSnapshot =>
  'coordinates' in value

export const useLocationProvider = () => {
  const [state, setState] = useState<LocationState>(initialState)
  const watchRef = useRef<number | null>(null)
  const accept = useCallback((snapshot: LocationSnapshot) => {
    saveLocationSnapshot(snapshot)
    setState({ status: 'granted', snapshot, permissionState: 'granted', retryable: true, message: 'Местоположение определено' })
    return snapshot
  }, [])
  const request = useCallback(async ({ allowBrowserFallback = true }: LocationRequest) => {
    setState(locationState('requesting'))
    const telegram = await requestTelegramLocation()
    if (isSnapshot(telegram)) return accept(telegram)
    if (telegram.status === 'denied' || !allowBrowserFallback) {
      setState(telegram)
      return telegram
    }
    const browser = await requestBrowserLocation()
    if (isSnapshot(browser)) return accept(browser)
    setState(browser)
    return browser
  }, [accept])
  const usePoint = useCallback((point: LocationPoint, source: LocationSource) => {
    if (!validCoordinate(point.latitude, point.longitude)) return setState(locationState('error'))
    accept(createSnapshot({
      accuracy: null, altitude: null, course: null,
      latitude: point.latitude, longitude: point.longitude, speed: null,
    }, source))
  }, [accept])
  const stopWatch = useCallback(() => {
    stopBrowserWatch(watchRef.current)
    watchRef.current = null
  }, [])
  const startWatch = useCallback(() => {
    stopWatch()
    setState((current) => ({ ...current, status: 'requesting', message: 'Определяем местоположение' }))
    watchRef.current = startBrowserWatch({ onLocation: accept, onError: setState })
  }, [accept, stopWatch])
  const clear = useCallback(() => {
    stopWatch()
    clearLocationSnapshot()
    setState(locationState('idle'))
  }, [stopWatch])
  useEffect(() => stopWatch, [stopWatch])
  return {
    ...state, request, startWatch, stopWatch, clear,
    useManualPoint: (point: LocationPoint) => usePoint(point, 'manual_map'),
    useCityCenter: (point: LocationPoint) => usePoint(point, 'city_center'),
    openTelegramSettings: openTelegramLocationSettings,
  }
}
