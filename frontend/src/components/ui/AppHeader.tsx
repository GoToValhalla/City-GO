import { useEffect, useState } from 'react'
import { Compass, MapPinned } from 'lucide-react'
import { Link, NavLink } from 'react-router-dom'
import { getAvailableCities } from '../../api/cities/cities.api'
import {
  DEFAULT_CITY,
  getCurrentCity,
  isPublishedCity,
  setCurrentCity,
  type CityOption,
} from '../../shared/city/currentCity'

type NavItem = {
  to: string
  label: string
  end?: boolean
}

const navItems: NavItem[] = [
  { to: '/', label: 'Главная', end: true },
  { to: '/places', label: 'Места' },
  { to: '/open-now', label: 'Открыто' },
  { to: '/nearby', label: 'Рядом' },
  { to: '/routes/generate', label: 'Маршрут' },
]

const navClass = ({ isActive }: { isActive: boolean }) => (
  isActive ? 'nav-link active' : 'nav-link'
)

export const AppHeader = () => {
  const [cities, setCities] = useState<CityOption[]>([DEFAULT_CITY])
  const [selectedCity, setSelectedCity] = useState<CityOption>(getCurrentCity())

  useEffect(() => {
    const loadCities = async () => {
      const currentCity = getCurrentCity()

      try {
        const availableCities = await getAvailableCities()

        if (availableCities.length === 0) {
          // Не подменяем сохранённый город фальшивым DEFAULT_CITY при временно
          // пустом ответе API: селектор и экран должны показывать один контекст.
          setCities([currentCity])
          setSelectedCity(currentCity)
          return
        }

        setCities(availableCities)

        const freshCurrentCity = availableCities.find((city) => city.slug === currentCity.slug)
        const nextCity = freshCurrentCity ?? availableCities[0]

        setSelectedCity(nextCity)
        setCurrentCity(nextCity)
      } catch (error) {
        console.error(error)
        setCities([currentCity])
        setSelectedCity(currentCity)
      }
    }

    loadCities()
  }, [])

  const handleCityChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const nextCity = cities.find((city) => city.slug === event.target.value) ?? selectedCity

    setSelectedCity(nextCity)
    setCurrentCity(nextCity)
  }

  return (
    <header className="app-header">
      <Link className="brand-link" to="/">
        <span className="brand-mark">
          <Compass size={22} />
        </span>
        <span>
          <span className="brand-kicker">городской навигатор</span>
          <span className="brand-title">City Go</span>
        </span>
      </Link>

      <nav className="main-nav" aria-label="Основная навигация">
        {navItems.map((item) => (
          <NavLink key={item.to} className={navClass} end={item.end} to={item.to}>
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="header-tools">
        <label className="city-context">
          <span>Город:</span>
          <select value={selectedCity.slug} onChange={handleCityChange}>
            {cities.map((city) => (
              <option key={city.slug} value={city.slug}>
                {city.name}
                {isPublishedCity(city) ? '' : ' · готовится'}
                {typeof city.places_count === 'number' ? ` · ${city.places_count} мест` : ''}
              </option>
            ))}
          </select>
        </label>

        <Link className="header-action" to="/places">
          <MapPinned size={16} />
          <span>Все места</span>
        </Link>
      </div>
    </header>
  )
}
