const CATEGORY_LABELS: Record<string, string> = {
  attraction: 'Достопримечательность',
  bar: 'Вечер',
  cafe: 'Кафе',
  coffee: 'Кофе',
  culture: 'Культура',
  food: 'Еда',
  hotel: 'Отель',
  museum: 'Музей',
  park: 'Парк',
  service: 'Сервис',
  walk: 'Прогулка',
}

const INTEREST_ALIASES: Record<string, string[]> = {
  culture: ['culture', 'museum', 'attraction'],
  museum: ['museum', 'culture', 'attraction'],
  quiet: ['park', 'walk', 'museum'],
  restaurant: ['food'],
  sea: ['sea', 'walk', 'park', 'attraction'],
  walk: ['walk', 'park', 'attraction'],
}

const PRICE_LABELS: Record<number, string> = {
  1: 'доступно',
  2: 'средний чек',
  3: 'выше среднего',
  4: 'дорого',
}

const CONFIDENCE_LABELS: Record<string, string> = {
  high: 'высокая уверенность',
  low: 'требует проверки',
  medium: 'средняя уверенность',
}

const SOURCE_LABELS: Record<string, string> = {
  manual_editorial: 'редакционная база',
  osm: 'OpenStreetMap',
  tourist_page: 'туристический источник',
}

export const categoryLabel = (category: string): string => {
  return CATEGORY_LABELS[category] ?? 'Место'
}

export const placeDescription = (
  description: string | null | undefined,
  title: string,
  category: string,
): string => {
  if (!description) return `${categoryLabel(category)}: ${title}`
  const prefix = `${category}: `
  return description.startsWith(prefix) ? description.slice(prefix.length) : description
}

export const priceLabel = (level: number | null | undefined): string => {
  return level && level > 0 ? PRICE_LABELS[level] ?? `уровень ${level}` : 'цена не указана'
}

export const timeLabel = (open?: string, close?: string): string => {
  return open && close ? `${open}-${close}` : 'часы уточняются'
}

const confidenceLabel = (confidence: string | number): string => {
  if (typeof confidence === 'number') return `уверенность ${Math.round(confidence * 100)}%`
  const numeric = Number(confidence)
  if (Number.isFinite(numeric)) return `уверенность ${Math.round(numeric * 100)}%`
  return CONFIDENCE_LABELS[confidence] ?? confidence
}

export const sourceLabel = (source?: string, confidence?: string | number): string => {
  const base = source ? SOURCE_LABELS[source] ?? source : 'локальный каталог'
  const level = confidence ? confidenceLabel(confidence) : null
  return level ? `${base}, ${level}` : base
}

export const interestMatches = (
  category: string,
  tags: string[],
  interest: string,
): boolean => {
  const aliases = INTEREST_ALIASES[interest] ?? [interest]
  return aliases.includes(category) || aliases.some((item) => tags.includes(item))
}
