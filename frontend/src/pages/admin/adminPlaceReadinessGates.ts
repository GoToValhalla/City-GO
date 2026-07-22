/** Derive place readiness gates from existing place-detail fields (no new API). */

export type PlaceGateInput = {
  image_url: string | null
  address: string | null
  opening_hours: Record<string, unknown> | null
  short_description: string | null
  category: string | null
  lat: number
  lng: number
  verification_status: string
  publication_status: string
  route_enabled: boolean
  route_exclusion_reason: string | null
  visible_to_users: boolean
}

export type ReadinessGate = {
  key: string
  ok: boolean
  detail: string
}

const hasHours = (value: Record<string, unknown> | null) => {
  if (!value) return false
  const display = value.display ?? value.raw
  if (typeof display === 'string') return display.trim().length > 0
  return Object.keys(value).length > 0
}

const hasCoords = (lat: number, lng: number) => (
  Number.isFinite(lat) && Number.isFinite(lng) && !(lat === 0 && lng === 0)
)

export const buildPlaceReadinessGates = (place: PlaceGateInput): ReadinessGate[] => [
  {
    key: 'photos',
    ok: Boolean(place.image_url?.trim()),
    detail: place.image_url?.trim() ? 'Есть основное фото' : 'Нет основного фото',
  },
  {
    key: 'address',
    ok: Boolean(place.address?.trim()),
    detail: place.address?.trim() ? place.address.trim() : 'Адрес не указан',
  },
  {
    key: 'opening_hours',
    ok: hasHours(place.opening_hours),
    detail: hasHours(place.opening_hours) ? 'Часы указаны' : 'Часы работы не указаны',
  },
  {
    key: 'description',
    ok: Boolean(place.short_description?.trim()),
    detail: place.short_description?.trim() ? 'Описание заполнено' : 'Нет короткого описания',
  },
  {
    key: 'category',
    ok: Boolean(place.category?.trim()),
    detail: place.category?.trim() ? place.category.trim() : 'Категория не задана',
  },
  {
    key: 'coordinates',
    ok: hasCoords(place.lat, place.lng),
    detail: hasCoords(place.lat, place.lng) ? `${place.lat}, ${place.lng}` : 'Координаты отсутствуют или нулевые',
  },
  {
    key: 'verification',
    ok: place.verification_status === 'verified',
    detail: place.verification_status === 'verified' ? 'Место подтверждено' : `Статус: ${place.verification_status}`,
  },
  {
    key: 'publication_eligibility',
    ok: place.publication_status === 'published' && place.visible_to_users,
    detail: place.publication_status === 'published' && place.visible_to_users
      ? 'Опубликовано и видно пользователям'
      : `Публикация: ${place.publication_status}; в каталоге: ${place.visible_to_users ? 'да' : 'нет'}${
        place.route_enabled ? '' : `; маршруты: нет${place.route_exclusion_reason ? ` (${place.route_exclusion_reason})` : ''}`
      }`,
  },
]
