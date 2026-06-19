import type { RecommendationRouteFormState } from '../../features/routes/model/recommendationRouteForm'
import { getCurrentCity, getCurrentCityCoordinates } from '../../shared/city/currentCity'

const currentCity = getCurrentCity()
const cityCoordinates = getCurrentCityCoordinates(currentCity.slug)

export const initialRouteForm: RecommendationRouteFormState = {
  lat: cityCoordinates.lat,
  lng: cityCoordinates.lng,
  startAddress: '',
  startSource: 'city_center',
  timeBudgetMinutes: '120',
  timeOfDay: '',
  routeTimeMode: 'flexible',
  useTimeBudget: true,
  interests: [],
  avoidedCategories: [],
  budgetLevel: '',
  paceMode: '',
  isVisiting: false,
  userId: 'web-user',
}
