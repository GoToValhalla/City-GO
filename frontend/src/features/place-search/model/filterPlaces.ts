import type { Place } from '../../../entities/place/model/types'
import { categoryLabel } from '../../../shared/place/categoryLabels'

const normalize = (value: string | null | undefined): string => (value ?? '').trim().toLowerCase()

export const filterPlaces = (places: Place[], search: string): Place[] => {
  const normalizedSearch = normalize(search)

  if (!normalizedSearch) {
    return places
  }

  return places.filter((place) => {
    const category = place.category ?? ''
    return [
      place.title,
      place.name,
      category,
      categoryLabel(category),
      place.address,
      place.short_description,
      place.description,
    ].some((value) => normalize(value).includes(normalizedSearch))
  })
}
