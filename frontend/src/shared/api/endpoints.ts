export const endpoints = {
  places: '/places/',
  placeBySlug: '/places/by-slug',
}

export const buildPlacesUrl = (citySlug: string, limit?: number, offset?: number): string => {
  const params = new URLSearchParams({ city_slug: citySlug })
  if (limit !== undefined) params.set('limit', String(limit))
  if (offset !== undefined) params.set('offset', String(offset))
  return `${endpoints.places}?${params.toString()}`
}

export const buildPlaceBySlugUrl = (slug: string): string => {
  return `${endpoints.placeBySlug}/${encodeURIComponent(slug)}`
}
