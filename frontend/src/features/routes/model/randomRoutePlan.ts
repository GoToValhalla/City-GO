export type RandomRouteMode = 'random_places' | 'random_mood'

export type RandomRoutePlan = {
  seed: number
  minutes: number
  categoryMode: 'none' | 'balanced'
  categories: string[]
}

const DURATION_OPTIONS = [60, 120, 180, 240] as const

const seededRandom = (seed: number): (() => number) => {
  let state = seed >>> 0
  return () => {
    state += 0x6d2b79f5
    let value = state
    value = Math.imul(value ^ (value >>> 15), value | 1)
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61)
    return ((value ^ (value >>> 14)) >>> 0) / 4_294_967_296
  }
}

export const parseRandomRouteMode = (value: string | null): RandomRouteMode => (
  value === 'random_mood' ? 'random_mood' : 'random_places'
)

export const nextRandomRouteSeed = (): number => (
  ((Date.now() >>> 0) ^ Math.floor(Math.random() * 0x7fffffff)) & 0x7fffffff
)

export const buildRandomRoutePlan = (
  mode: RandomRouteMode,
  availableCategories: string[],
  selectedMinutes: number,
  seed: number,
): RandomRoutePlan => {
  if (mode === 'random_places') {
    return { seed, minutes: selectedMinutes, categoryMode: 'none', categories: [] }
  }

  const categories = [...new Set(availableCategories.filter(Boolean))].sort()
  if (!categories.length) throw new Error('Для случайного настроения нужны категории города.')

  const random = seededRandom(seed)
  const minutes = DURATION_OPTIONS[Math.floor(random() * DURATION_OPTIONS.length)]
  const ranked = categories.map((category) => ({ category, rank: random() }))
    .sort((left, right) => left.rank - right.rank)
  const limit = Math.min(ranked.length, 1 + Math.floor(random() * Math.min(3, ranked.length)))

  return { seed, minutes, categoryMode: 'balanced', categories: ranked.slice(0, limit).map((item) => item.category) }
}
