import { useCallback, useEffect, useState } from 'react'
import { getAvailableCities } from '../../../api/cities/cities.api'
import { getCurrentCity, setCurrentCity, type CityOption } from '../../../shared/city/currentCity'

type CityState = {
  cities: CityOption[]
  selectedCity: CityOption
  loading: boolean
  error: string | null
}

const requestCityState = async (saved: CityOption): Promise<CityState> => {
  try {
    const available = await getAvailableCities()
    const cities = available.length ? available : [saved]
    const selectedCity = cities.find((city) => city.slug === saved.slug) ?? cities[0]
    return { cities, selectedCity, loading: false, error: null }
  } catch (error) {
    console.error(error)
    return { cities: [saved], selectedCity: saved, loading: false, error: 'Не удалось обновить список городов.' }
  }
}

export const useAvailableCities = () => {
  const current = getCurrentCity()
  const [state, setState] = useState<CityState>({
    cities: [current], selectedCity: current, loading: true, error: null,
  })

  const reload = useCallback(async () => {
    setState((value) => ({ ...value, loading: true, error: null }))
    const saved = getCurrentCity()
    const next = await requestCityState(saved)
    setState(next)
    if (next.selectedCity.slug !== saved.slug) setCurrentCity(next.selectedCity)
  }, [])

  useEffect(() => {
    let active = true
    const saved = getCurrentCity()
    void requestCityState(saved).then((next) => {
      if (!active) return
      setState(next)
      if (next.selectedCity.slug !== saved.slug) setCurrentCity(next.selectedCity)
    })
    return () => { active = false }
  }, [])
  useEffect(() => {
    const sync = () => setState((value) => ({ ...value, selectedCity: getCurrentCity() }))
    window.addEventListener('citygo:city-changed', sync)
    return () => window.removeEventListener('citygo:city-changed', sync)
  }, [])

  const selectCity = (selectedCity: CityOption) => {
    setState((value) => ({ ...value, selectedCity }))
    setCurrentCity(selectedCity)
  }

  return { ...state, reload, selectCity }
}
