export type AddressPlace = {
  address: string
  category: string
  lat?: number | null
  lng?: number | null
}

const PLACEHOLDER_ADDRESSES = new Set([
  '',
  'адрес уточняется',
  'адрес не указан',
  'нет адреса',
  'unknown',
  '-',
])

const GENERIC_EXACT = new Set([
  'центр города',
  'у моря',
  'променад',
  'центральный променад',
  'парк',
])

const VENUE_CATEGORIES = new Set(['cafe', 'coffee', 'food', 'restaurant', 'museum', 'gallery', 'culture'])
const STREET_HINT = /(ул\.|улица|проспект|пр\.|пер\.|переулок|наб\.|набережная|шоссе|бульвар|б-р|пл\.|площадь|\d)/i

export const UNCLEAR_ADDRESS_LABEL = 'Адрес уточняется'
export const MAP_LINK_LABEL = 'Открыть на карте'

export const normalizeRawAddress = (address?: string | null): string => (address ?? '').trim()

export const isPlaceholderAddress = (address?: string | null): boolean => {
  const raw = normalizeRawAddress(address)
  const lowered = raw.toLowerCase()
  if (!raw) return true
  if (PLACEHOLDER_ADDRESSES.has(lowered)) return true
  return lowered.startsWith('координаты ') || lowered.includes('координаты')
}

export const isGenericAddress = (address?: string | null, category?: string | null): boolean => {
  const raw = normalizeRawAddress(address)
  if (!raw || isPlaceholderAddress(raw)) return false
  const lowered = raw.toLowerCase()
  if (GENERIC_EXACT.has(lowered)) return true
  const cat = (category ?? '').toLowerCase()
  if (!VENUE_CATEGORIES.has(cat)) return false
  if (STREET_HINT.test(raw)) return false
  return raw.length < 28
}

export const hasRealAddress = (address?: string | null, category?: string | null): boolean => {
  const raw = normalizeRawAddress(address)
  if (!raw || isPlaceholderAddress(raw)) return false
  return !isGenericAddress(raw, category)
}

export const googleMapUrl = (lat: number, lng: number): string =>
  `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`

export const placeAddressView = (place: AddressPlace) => {
  const real = hasRealAddress(place.address, place.category)
  const lat = place.lat ?? null
  const lng = place.lng ?? null
  const mapUrl = lat != null && lng != null ? googleMapUrl(lat, lng) : null
  return {
    label: real ? normalizeRawAddress(place.address) : UNCLEAR_ADDRESS_LABEL,
    unclear: !real,
    mapUrl,
  }
}
