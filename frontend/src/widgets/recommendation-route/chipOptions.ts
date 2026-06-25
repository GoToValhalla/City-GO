export type InterestOption = {
  value: string
  label: string
}

export type RouteFeature = 'sea'

export const interestOptions: InterestOption[] = [
  { value: 'coffee', label: 'Кофе' },
  { value: 'food', label: 'Еда' },
  { value: 'sea', label: 'Вода' },
  { value: 'walk', label: 'Прогулка' },
  { value: 'quiet', label: 'Тихо' },
  { value: 'museum', label: 'Музеи' },
]

const interestFeatureByValue: Record<string, RouteFeature | null> = {
  coffee: null,
  food: null,
  sea: 'sea',
  walk: null,
  quiet: null,
  museum: null,
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

export const filterCategoryOptionsForFeatures = <T extends { code: string }>(categories: T[], routeFeatures: string[]): T[] => {
  return categories.filter((category) => featuresSupportInterest(routeFeatures, category.code))
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
