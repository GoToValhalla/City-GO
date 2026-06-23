import type { Place } from '../../../entities/place/model/types'
import { categoryLabel } from '../../../shared/place/categoryLabels'

const normalize = (value: string | null | undefined): string => (value ?? '').trim().toLowerCase()

export const filterPlaces = (places: Place[], search: string): Place[] => {
  const normalizedSearch = normalize(search)

  if (!normalizedSearch) {
    return places
  }

  return places.filter((place) => {
    return [
      place.title,
      place.name,
      place.category,
      categoryLabel(place.category),
      place.address,
      place.short_description,
      place.description,
    ].some((value) => normalize(value).includes(normalizedSearch))
  })
}
