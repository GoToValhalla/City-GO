export type CityOption = {
  slug: string
  name: string
  country: string
  region?: string | null
  launch_status?: string
  places_count?: number
}

export type CityCoordinates = {
  lat: string
  lng: string
}

const STORAGE_KEY = 'citygo:selectedCity'

export const DEFAULT_CITY: CityOption = {
  slug: 'zelenogradsk',
  name: 'Зеленоградск',
  country: 'Россия',
  region: 'Калининградская область',
  launch_status: 'published',
  places_count: 0,
}

const CITY_COORDINATES: Record<string, CityCoordinates> = {
  zelenogradsk: {
    lat: '54.96',
    lng: '20.48',
  },
  astrakhan: {
    lat: '46.3497',
    lng: '48.0408',
  },
  arkhangelsk: {
    lat: '64.5393',
    lng: '40.5170',
  },
  kutaisi: {
    lat: '42.2676',
    lng: '42.7180',
  },
  yerevan: {
    lat: '40.1792',
    lng: '44.4991',
  },
  'khanty-mansiysk': {
    lat: '61.0042',
    lng: '69.0019',
  },
  kaliningrad: {
    lat: '54.7104',
    lng: '20.4522',
  },
  'rostov-on-don': {
    lat: '47.2225',
    lng: '39.7185',
  },
  almaty: {
    lat: '43.2380',
    lng: '76.9450',
  },
  алматы: {
    lat: '43.2380',
    lng: '76.9450',
  },
}

export const getCurrentCity = (): CityOption => {
  if (typeof window === 'undefined') {
    return DEFAULT_CITY
  }

  const saved = window.localStorage.getItem(STORAGE_KEY)

  if (!saved) {
    return DEFAULT_CITY
  }

  try {
    const parsed = JSON.parse(saved) as CityOption

    if (!parsed.slug || !parsed.name) {
      return DEFAULT_CITY
    }

    return parsed
  } catch {
    return DEFAULT_CITY
  }
}

export const setCurrentCity = (city: CityOption): void => {
  if (typeof window === 'undefined') {
    return
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(city))
  window.dispatchEvent(new CustomEvent('citygo:city-changed', { detail: city }))
}

export const getCurrentCityCoordinates = (citySlug?: string): CityCoordinates => {
  const slug = citySlug || getCurrentCity().slug
  const coordinates = CITY_COORDINATES[slug]

  if (!coordinates) {
    throw new Error(`Нет координат города: ${slug}`)
  }

  return coordinates
}

export const isPublishedCity = (city: CityOption): boolean => {
  return city.launch_status === 'published'
}
