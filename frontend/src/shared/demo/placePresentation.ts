import type { Place } from '../../entities/place/model/types'
import { categoryLabel } from '../place/categoryLabels'

const GENERIC_BY_CATEGORY: Record<string, string> = {
  bar: 'Вечерняя точка для маршрута, которую стоит проверить по часам перед визитом.',
  coffee: 'Кофейная остановка для короткой паузы по пути.',
  food: 'Место для обеда или ужина внутри прогулки.',
  museum: 'Культурная остановка для спокойного маршрута.',
  park: 'Зелёная точка для паузы и прогулки.',
  walk: 'Прогулочная точка маршрута с открытым форматом визита.',
}

const RAW_PREFIX = /^[\p{L}_ -]{2,32}:\s*/iu

export const cleanPlaceDescription = (place: Place): string => {
  const raw = (place.short_description ?? '').trim()
  const cleaned = raw.replace(RAW_PREFIX, '').trim()
  if (cleaned && cleaned !== place.title) return cleaned
  return GENERIC_BY_CATEGORY[place.category] ?? `${categoryLabel(place.category)} в городском каталоге.`
}

export const verifiedImageUrl = (place: Place): string | null => {
  if (place.image?.match_status === 'exact_place_photo') return place.image.url ?? place.image_url ?? null
  if (place.image_is_exact === true) return place.image_url ?? null
  if (place.image_source_type && place.image_url) return place.image_url
  return null
}

export const photoStateLabel = (place: Place): string => {
  if (verifiedImageUrl(place)) return 'Фото места'
  if (place.image?.match_status === 'area_photo') return 'Фото района рядом'
  if (place.image_source_type && place.image_url) return 'Фото места'
  if (place.image_url) return 'Фото требует проверки'
  return 'Нет проверенного фото'
}

export const placeFeatureLabels = (place: Place): string[] => {
  return [
    place.indoor ? 'в помещении' : '',
    place.outdoor ? 'на улице' : '',
    place.family_friendly ? 'с семьёй' : '',
    place.dog_friendly ? 'с собакой' : '',
  ].filter(Boolean)
}
