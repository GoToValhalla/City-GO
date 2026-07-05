export const RESERVED_CITY_ROUTE_SLUGS = new Set([
  'admin',
  'city-selection',
  'nearby',
  'open-now',
  'places',
  'routes',
  'walk-route',
  'telegram',
])

export const isReservedCityRouteSlug = (slug: string): boolean => RESERVED_CITY_ROUTE_SLUGS.has(slug)
