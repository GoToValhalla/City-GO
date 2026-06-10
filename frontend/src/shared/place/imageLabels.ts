import type { PlaceImage, PlaceImageMatchStatus } from '../../entities/place/model/types'

const STATUS_LABELS: Record<PlaceImageMatchStatus, string> = {
  area_photo: 'Фото района рядом',
  category_photo: 'Иллюстрация категории',
  exact_place_photo: 'Фото места',
  no_photo: 'Фото недоступно',
}

const CONFIDENCE_LABELS: Record<string, string> = {
  high: 'проверено автоматически',
  low: 'не выдаём за фото места',
  medium: 'гео-совпадение',
}

export const imageStatusLabel = (image?: PlaceImage): string => {
  return STATUS_LABELS[image?.match_status ?? 'no_photo']
}

export const imageConfidenceLabel = (image?: PlaceImage): string => {
  return CONFIDENCE_LABELS[image?.match_confidence ?? 'low']
}
