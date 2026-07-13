import { ArrowRight, MapPin, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { Place } from '../../entities/place/model/types'
import { cityCatalogPath, cityRouteBuildPath } from '../../features/city-routing/cityPaths'
import { cityLocation } from '../../features/city-search/model/citySearch'
import type { CityOption } from '../../shared/city/currentCity'
import { HomeCityMap } from './HomeCityMap'

type Props = {
  categoriesCount: number
  city: CityOption
  places: Place[]
  placesTotal: number
}

const openCityPicker = () => window.dispatchEvent(new CustomEvent('citygo:open-city-picker'))

export const HomeHero = ({ categoriesCount, city, places, placesTotal }: Props) => (
  <section className="hero-section">
    <div className="hero-copy">
      <button className="hero-location" onClick={openCityPicker} type="button">
        <MapPin size={16} /><span>{cityLocation(city)}</span><span aria-hidden="true">›</span>
      </button>
      <p className="hero-eyebrow">Город на ладони</p>
      <h1 className="hero-title">{city.name}</h1>
      <p className="hero-text">Смотрите опубликованные места на карте и собирайте прогулку из реальных данных CITY GO.</p>
      <div className="hero-actions">
        <Link className="hero-cta-link" to={cityCatalogPath(city.slug)}>Смотреть места <ArrowRight size={18} /></Link>
        <Link className="hero-cta-link secondary" to={`${cityRouteBuildPath(city.slug)}?mode=random_mood`}><Sparkles size={18} /> Удивить меня</Link>
      </div>
      <div className="hero-facts" aria-label="Данные города">
        <span><strong>{placesTotal || city.places_count || 0}</strong> опубликованных мест</span>
        {categoriesCount ? <span><strong>{categoriesCount}</strong> категорий</span> : null}
      </div>
    </div>
    <HomeCityMap city={city} places={places} />
  </section>
)
