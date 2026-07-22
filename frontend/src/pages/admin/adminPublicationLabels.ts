/** Shared Russian labels for admin publication / readiness diagnostics. */

export const GATE_LABELS: Record<string, string> = {
  photos: 'Фото',
  address: 'Адрес',
  opening_hours: 'Часы работы',
  description: 'Описание',
  category: 'Категория',
  coordinates: 'Координаты',
  verification: 'Проверка',
  publication_eligibility: 'Готовность к публикации',
}

export const BLOCKER_LABELS: Record<string, string> = {
  no_photo: 'без фото',
  no_address: 'без адреса',
  no_description: 'без описания',
  no_hours: 'без часов работы',
  low_quality: 'низкое качество',
  stale: 'нужна перепроверка',
  route_ineligible: 'исключены из маршрутов',
  excluded_by_design: 'исключено правилами',
  possible_duplicates: 'возможные дубли',
  pending_reviews: 'заявки на проверку',
  missing_category: 'нет категории',
  missing_coordinates: 'нет координат',
}

export const SECTION_LABELS: Record<string, string> = {
  address: 'адреса',
  photo: 'фото',
  description: 'описания',
  category: 'категории',
  coordinates: 'координаты',
  opening_hours: 'время работы',
  pending_reviews: 'заявки на проверку',
  verification: 'проверки',
}

export const BOOTSTRAP_LABELS: Record<string, string> = {
  NO_SCOPES: 'нет контуров',
  NO_ENABLED_SCOPES: 'нет включённых контуров',
  INVALID_SCOPE_GEOMETRY: 'проверьте координаты контура',
}

export const gateLabel = (key: string) => GATE_LABELS[key] ?? key.replace(/[_-]+/g, ' ')
export const blockerLabel = (key: string) => BLOCKER_LABELS[key] ?? key.replace(/[_-]+/g, ' ')
export const sectionLabel = (key: string) => SECTION_LABELS[key] ?? key
export const bootstrapLabel = (key: string) => BOOTSTRAP_LABELS[key] ?? key

export const primaryBlockerSentence = (
  primary: string | null | undefined,
  blockers?: Record<string, number> | null,
) => {
  if (!primary) return null
  const count = blockers?.[primary]
  const label = blockerLabel(primary)
  return count != null ? `Главный блокер: ${label} (${count})` : `Главный блокер: ${label}`
}
