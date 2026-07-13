import type { CityOption } from '../../../shared/city/currentCity'

const normalize = (value: string): string => (
  value.trim().toLocaleLowerCase('ru').replace(/\s+/g, ' ')
)

export const cityLocation = (city: CityOption): string => (
  [city.region, city.country]
    .filter((value, index, values): value is string => Boolean(value) && values.indexOf(value) === index)
    .join(' · ')
)

export const cityIdentity = (city: CityOption): string => {
  const location = cityLocation(city)
  return location ? `${city.name} · ${location}` : city.name
}

export const filterCities = (cities: CityOption[], query: string): CityOption[] => {
  const term = normalize(query)
  const sorted = [...cities].sort((left, right) => (
    cityIdentity(left).localeCompare(cityIdentity(right), 'ru')
  ))

  if (!term) return sorted

  return sorted.filter((city) => normalize(
    `${city.name} ${city.region ?? ''} ${city.country} ${city.slug}`,
  ).includes(term))
}
