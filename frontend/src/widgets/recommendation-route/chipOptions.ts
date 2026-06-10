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

export const avoidedCategoryOptions = [
  { value: 'bar', label: 'Бары' },
  { value: 'museum', label: 'Музеи' },
  { value: 'restaurant', label: 'Рестораны' },
]
