import { Map, Route, Search, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { cityCatalogPath, cityRouteBuildPath } from '../../features/city-routing/cityPaths'
import { getCurrentCity } from '../../shared/city/currentCity'
import { LocationCarousel } from './LocationCarousel'

type HomeHeroProps = {
  search: string
  cityName?: string
  onSearchChange: (value: string) => void
}

export const HomeHero = ({ search, cityName = 'выбранном городе', onSearchChange }: HomeHeroProps) => {
  const citySlug = getCurrentCity().slug
  return (
    <section className="hero-section">
      <div className="hero-copy">
        <span className="hero-badge">
          <Sparkles size={16} />
          Гид по городу и маршрутам
        </span>

        <h1 className="hero-title">Найди куда сходить: {cityName}</h1>

        <p className="hero-text">
          Ищи места, проверяй что открыто сейчас и собирай прогулку под время,
          интересы и компанию.
        </p>

        <label className="hero-search">
          <Search size={20} aria-hidden="true" />
          <input
            type="text"
            placeholder="Кафе, музей, парк, адрес..."
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
          />
        </label>

        <div className="hero-actions">
          <Link className="hero-cta-link" to={cityRouteBuildPath(citySlug)}>
            <Route size={17} />
            Собрать маршрут
          </Link>
          <Link className="hero-cta-link secondary" to={cityCatalogPath(citySlug)}>
            <Map size={17} />
            Смотреть места
          </Link>
        </div>
      </div>

      <div className="hero-route-preview">
        <span className="preview-kicker">Сегодня</span>
        <strong>2 часа в городе</strong>
        <ol>
          <li>Кофе или прогулка</li>
          <li>Интересное место рядом</li>
          <li>Финальная точка маршрута</li>
        </ol>
        <Link className="preview-link" to={cityRouteBuildPath(citySlug)}>Настроить маршрут</Link>
      </div>
      <LocationCarousel />
    </section>
  )
}