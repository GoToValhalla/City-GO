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

export const useNearbySearch = () => {
  const [city, setCity] = useState(getCurrentCity)
  const [radiusKm, setRadiusKm] = useState(0.3)
  const [point, setPoint] = useState<LocationPoint | null>(() => centerPoint(getCurrentCity()))
  const [source, setSource] = useState<'city_center' | 'device' | 'manual'>('city_center')
  const [places, setPlaces] = useState<NearbyPlace[]>([])
  const [suggestion, setSuggestion] = useState<NearestCitySuggestion | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const location = useLocationProvider()

  useEffect(() => {
    const syncCity = () => {
      const next = getCurrentCity()
      setCity(next)
      setPoint(centerPoint(next))
      setSource('city_center')
      setSuggestion(null)
    }
    window.addEventListener('citygo:city-changed', syncCity)
    return () => window.removeEventListener('citygo:city-changed', syncCity)
  }, [])

  useEffect(() => {
    if (!point) {
      setLoading(false)
      setPlaces([])
      return
    }
    let active = true
    setLoading(true)
    void getNearbyPlaces(point.latitude, point.longitude, radiusKm)
      .then((items) => { if (active) { setPlaces(items); setError(null) } })
      .catch(() => { if (active) setError('Не удалось загрузить места рядом') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [point, radiusKm])

  useEffect(() => {
    if (!point || source === 'city_center') return setSuggestion(null)
    let active = true
    void getNearestCitySuggestion(point.latitude, point.longitude)
      .then((row) => { if (active) setSuggestion(row?.city_slug !== city.slug ? row : null) })
    return () => { active = false }
  }, [city.slug, point, source])

  const requestLocation = useCallback(async () => {
    const result = await location.request({ scenario: 'nearby' })
    if (isSnapshot(result)) {
      setPoint(result.coordinates)
      setSource('device')
    }
  }, [location])
  const selectManual = useCallback((next: LocationPoint) => {
    location.useManualPoint(next)
    setPoint(next)
    setSource('manual')
  }, [location])
  const useCenter = useCallback(() => {
    const next = centerPoint(city)
    if (!next) return
    location.useCityCenter(next)
    setPoint(next)
    setSource('city_center')
  }, [city, location])

  return {
    city, error, loading, location, places, point, radiusKm, setRadiusKm,
    source, suggestion, requestLocation, selectManual, useCenter,
  }
}
