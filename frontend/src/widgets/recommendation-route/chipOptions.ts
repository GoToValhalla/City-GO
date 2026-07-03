export type InterestOption = {
  value: string
  label: string
}

export type RouteFeature = 'sea'

export const interestOptions: InterestOption[] = [
  { value: 'coffee', label: 'Кофе' },
  { value: 'food', label: 'Еда' },
  { value: 'sea', label: 'Море' },
  { value: 'walk', label: 'Прогулка' },
  { value: 'quiet', label: 'Тихо' },
  { value: 'museum', label: 'Музеи' },
]

const routeBlockedCategoryValues = new Set([
  'medical', 'medicine', 'health', 'healthcare', 'hospital', 'clinic', 'pharmacy', 'apteka', 'здоровье', 'медицина', 'аптека',
  'bank', 'atm', 'parking', 'fuel', 'toilet', 'toilets', 'public_toilet', 'банк', 'банкомат', 'парковка', 'туалет',
  'police', 'bus_stop', 'stop', 'transport', 'public_transport', 'остановка', 'транспорт',
  'service', 'services', 'utility', 'useful', 'generic_service', 'полезное', 'сервис', 'услуги',
  'industrial', 'shelter', 'post_office', 'vending_machine', 'bench', 'waste_basket', 'charging_station',
  'car_service', 'mvd', 'government', 'military', 'cemetery', 'waste_disposal',
  'unknown', 'other', 'office', 'hotel', 'shopping', 'shop', 'supermarket', 'shopping_mall', 'mall',
])

const interestFeatureByValue: Record<string, RouteFeature | null> = {
  beach: 'sea',
  coast: 'sea',
  coastal: 'sea',
  coffee: null,
  food: null,
  promenade: 'sea',
  sea: 'sea',
  seaside: 'sea',
  walk: null,
  quiet: null,
  museum: null,
}

const normalizeOptionValue = (value: unknown): string => String(value ?? '').trim().toLowerCase()

export const isRouteBlockedCategoryOption = (category: { code?: string; name?: string }): boolean => {
  const code = normalizeOptionValue(category.code)
  const name = normalizeOptionValue(category.name)
  return routeBlockedCategoryValues.has(code) || routeBlockedCategoryValues.has(name)
}

export const featuresSupportInterest = (routeFeatures: string[], interest: string): boolean => {
  const requiredFeature = interestFeatureByValue[interest]

  if (!requiredFeature) {
    return true
  }

  return routeFeatures.includes(requiredFeature)
}

export const getInterestOptionsForFeatures = (routeFeatures: string[]): InterestOption[] => {
  return interestOptions.filter((option) => featuresSupportInterest(routeFeatures, option.value))
}

export const filterInterestsForFeatures = (interests: string[], routeFeatures: string[]): string[] => {
  return interests.filter((interest) => featuresSupportInterest(routeFeatures, interest))
}

export const filterCategoryOptionsForFeatures = <T extends { code: string; name?: string }>(categories: T[], routeFeatures: string[]): T[] => {
  return categories.filter((category) => !isRouteBlockedCategoryOption(category) && featuresSupportInterest(routeFeatures, category.code))
}

export const getUnsupportedInterestLabels = (interests: string[], routeFeatures: string[]): string[] => {
  const optionByValue = new Map(interestOptions.map((option) => [option.value, option.label]))
  return interests
    .filter((interest) => !featuresSupportInterest(routeFeatures, interest))
    .map((interest) => optionByValue.get(interest) ?? interest)
}

export const avoidedCategoryOptions = [
  { value: 'bar', label: 'Бары' },
  { value: 'museum', label: 'Музеи' },
  { value: 'restaurant', label: 'Рестораны' },
]
