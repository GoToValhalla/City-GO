import type { MapManualPoint } from './mapTypes'

export const yandexMapLink = ({ latitude, longitude }: MapManualPoint): string =>
  `https://yandex.ru/maps/?pt=${longitude},${latitude}&z=16&l=map`

export const twoGisMapLink = ({ latitude, longitude }: MapManualPoint): string =>
  `https://2gis.ru/geo/${longitude}%2C${latitude}?m=${longitude}%2C${latitude}%2F16`
