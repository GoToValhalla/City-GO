import type { RecommendationRouteFormState } from '../../features/routes/model/recommendationRouteForm'
import { DEFAULT_CITY, getCurrentCity, getCurrentCityCoordinates } from '../../shared/city/currentCity'

const resolveInitialCoordinates = () => {
  const currentCity = getCurrentCity()
  try {
    return getCurrentCityCoordinates(currentCity.slug)
  } catch {
    return getCurrentCityCoordinates(DEFAULT_CITY.slug)
  }
}

export const buildInitialRouteForm = (): RecommendationRouteFormState => {
  const cityCoordinates = resolveInitialCoordinates()

  return {
    lat: cityCoordinates.lat,
    lng: cityCoordinates.lng,
    startAddress: '',
    startSource: 'city_center',
    timeBudgetMinutes: '120',
    timeOfDay: '',
    routeTimeMode: 'flexible',
    useTimeBudget: true,
    buildMode: 'auto',
    interests: [],
    avoidedCategories: [],
    budgetLevel: '',
    paceMode: '',
    isVisiting: false,
    userId: 'web-user',
    routeSlots: [],
  }
}
