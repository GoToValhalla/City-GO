import { Compass, Home, List, MapPin, Route } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { cityCatalogPath, cityHomePath, cityRouteBuildPath } from '../../features/city-routing/cityPaths'
import { cityLocation } from '../../features/city-search/model/citySearch'
import { useAvailableCities } from '../../features/city-search/model/useAvailableCities'
import { CityPicker } from '../../features/city-search/ui/CityPicker'
import type { CityOption } from '../../shared/city/currentCity'
import { useTheme } from '../../shared/theme/useTheme'
import { ThemeToggle } from './ThemeToggle'

const navClass = ({ isActive }: { isActive: boolean }) => isActive ? 'nav-link active' : 'nav-link'

export const AppHeader = () => {
  const cityState = useAvailableCities()
  const { mode: themeMode, setThemeMode } = useTheme()
  const [pickerOpen, setPickerOpen] = useState(false)
  const navigate = useNavigate()
  const closePicker = useCallback(() => setPickerOpen(false), [])
  const home = cityHomePath(cityState.selectedCity.slug)
  const catalog = cityCatalogPath(cityState.selectedCity.slug)
  const route = cityRouteBuildPath(cityState.selectedCity.slug)

  useEffect(() => {
    const open = () => setPickerOpen(true)
    window.addEventListener('citygo:open-city-picker', open)
    return () => window.removeEventListener('citygo:open-city-picker', open)
  }, [])

  const selectCity = (city: CityOption) => {
    cityState.selectCity(city)
    closePicker()
    navigate(cityHomePath(city.slug))
  }

  return <>
    <header className="app-header">
      <Link aria-label="На главную" className="brand-link" to={home}>
        <span className="brand-mark"><Compass size={19} /></span><strong>CITY GO</strong>
      </Link>
      <nav className="main-nav" aria-label="Основная навигация">
        <NavLink className={navClass} to={catalog}>Места</NavLink>
        <NavLink className={navClass} to={route}>Маршрут</NavLink>
      </nav>
      <button className="city-context" onClick={() => setPickerOpen(true)} type="button">
        <MapPin size={17} /><span><strong>{cityState.selectedCity.name}</strong><small>{cityLocation(cityState.selectedCity)}</small></span><span aria-hidden="true">›</span>
      </button>
      <ThemeToggle className="theme-toggle--desktop" mode={themeMode} onChange={setThemeMode} />
    </header>
    <nav aria-label="Мобильная навигация" className="mobile-nav">
      <NavLink className={navClass} end to={home}><Home size={20} /><span>Главная</span></NavLink>
      <NavLink className={navClass} to={catalog}><List size={20} /><span>Места</span></NavLink>
      <NavLink className={navClass} to={route}><Route size={21} /><span>Маршрут</span></NavLink>
      <ThemeToggle className="theme-toggle--mobile" mode={themeMode} onChange={setThemeMode} />
    </nav>
    {pickerOpen ? <CityPicker cities={cityState.cities} error={cityState.error} loading={cityState.loading} onClose={closePicker} onRetry={() => void cityState.reload()} onSelect={selectCity} selectedCity={cityState.selectedCity} /> : null}
  </>
}
