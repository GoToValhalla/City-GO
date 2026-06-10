import type { Place } from '../../../entities/place/model/types'

export const filterPlaces = (places: Place[], search: string): Place[] => {
  const normalizedSearch = search.trim().toLowerCase()

  if (!normalizedSearch) {
    return places
  }

  return places.filter((place) => {
    return (
      place.title.toLowerCase().includes(normalizedSearch) ||
      place.category.toLowerCase().includes(normalizedSearch) ||
      place.address.toLowerCase().includes(normalizedSearch)
    )
  })
}
