import { useCallback, useEffect, useState } from 'react'
import {
  getNearbyPlaces, getNearestCitySuggestion,
  type NearbyPlace, type NearestCitySuggestion,
} from '../../api/nearby/nearby.api'
import { getCurrentCity, type CityOption } from '../../shared/city/currentCity'
import { useLocationProvider } from '../../shared/location/useLocationProvider'
import type { LocationPoint, LocationSnapshot } from '../../shared/location/types'
import { getNearbyCityCenter } from './nearbyCityCenter'

const centerPoint = (city: CityOption): LocationPoint | null => {
  const center = getNearbyCityCenter(city)
  return center.lat === null || center.lng === null
    ? null
    : { latitude: center.lat, longitude: center.lng }
}

const isSnapshot = (value: object): value is LocationSnapshot => 'coordinates' in value
const isAbortError = (value: unknown): boolean => value instanceof DOMException && value.name === 'AbortError'

export const useNearbySearch = () => {
  const [city, setCity] = useState(getCurrentCity)
  const [radiusKm, setRadiusKm] = useState(0.3)
  const [point, setPoint] = useState<LocationPoint | null>(() => centerPoint(getCurrentCity()))
  const [source, setSource] = useState<'city_center' | 'device' | 'manual'>('city_center')
  const [places, setPlaces] = useState<NearbyPlace[]>([])
  const [suggestion, setSuggestion] = useState<NearestCitySuggestion | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadToken, setReloadToken] = useState(0)
  const location = useLocationProvider()

  const reload = useCallback(() => setReloadToken((current) => current + 1), [])

  useEffect(() => {
    const syncCity = () => {
      const next = getCurrentCity()
      setCity(next)
      setPoint(centerPoint(next))
      setSource('city_center')
      setSuggestion(null)
      setError(null)
      setReloadToken((current) => current + 1)
    }
    window.addEventListener('citygo:city-changed', syncCity)
    return () => window.removeEventListener('citygo:city-changed', syncCity)
  }, [])

  useEffect(() => {
    if (!point) {
      setLoading(false)
      setPlaces([])
      return undefined
    }
    const controller = new AbortController()
    let active = true
    setLoading(true)
    void getNearbyPlaces(point.latitude, point.longitude, radiusKm, controller.signal)
      .then((items) => {
        if (!active) return
        setPlaces(items)
        setError(null)
      })
      .catch((err: unknown) => {
        if (!active || isAbortError(err)) return
        setError('Не удалось обновить места рядом. Проверь соединение и попробуй снова.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => {
      active = false
      controller.abort()
    }
  }, [point, radiusKm, reloadToken])

  useEffect(() => {
    if (!point || source === 'city_center') {
      setSuggestion(null)
      return undefined
    }
    let active = true
    void getNearestCitySuggestion(point.latitude, point.longitude)
      .then((row) => { if (active) setSuggestion(row?.city_slug !== city.slug ? row : null) })
    return () => { active = false }
  }, [city.slug, point, source])

  useEffect(() => {
    const restoreAfterSafariResume = () => {
      if (document.visibilityState === 'visible') reload()
    }
    document.addEventListener('visibilitychange', restoreAfterSafariResume)
    window.addEventListener('pageshow', reload)
    return () => {
      document.removeEventListener('visibilitychange', restoreAfterSafariResume)
      window.removeEventListener('pageshow', reload)
    }
  }, [reload])

  const requestLocation = useCallback(async () => {
    const result = await location.request({ scenario: 'nearby' })
    if (isSnapshot(result)) {
      setPoint(result.coordinates)
      setSource('device')
      setError(null)
    }
  }, [location])
  const selectManual = useCallback((next: LocationPoint) => {
    location.useManualPoint(next)
    setPoint(next)
    setSource('manual')
    setError(null)
  }, [location])
  const useCenter = useCallback(() => {
    const next = centerPoint(city)
    if (!next) return
    location.useCityCenter(next)
    setPoint(next)
    setSource('city_center')
    setError(null)
  }, [city, location])

  return {
    city, error, loading, location, places, point, radiusKm, reload, setRadiusKm,
    source, suggestion, requestLocation, selectManual, useCenter,
  }
}
