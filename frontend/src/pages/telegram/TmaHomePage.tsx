import { ChevronRight, MapPin } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CityPicker } from '../../features/city-search/ui/CityPicker'
import { useAvailableCities } from '../../features/city-search/model/useAvailableCities'
import { cityLocation } from '../../features/city-search/model/citySearch'
import type { CityOption } from '../../shared/city/currentCity'
import { TmaShell } from './TmaShell'

export const TmaHomePage = () => {
  const cityState = useAvailableCities()
  const [pickerOpen, setPickerOpen] = useState(false)
  const navigate = useNavigate()

  const selectCity = (city: CityOption) => {
    cityState.selectCity(city)
    setPickerOpen(false)
    navigate('/telegram/places')
  }

  return <TmaShell title="City GO">
    <section className="tma-place-card">
      <span className="telegram-map-pin" aria-hidden="true"><MapPin size={20} /></span>
      <div className="tma-place-card-body">
        <strong>{cityState.selectedCity.name}</strong>
        <span>{cityLocation(cityState.selectedCity)}</span>
      </div>
    </section>
    <button type="button" className="cg-button cg-button--primary" onClick={() => setPickerOpen(true)}>
      Выбрать город <ChevronRight size={16} />
    </button>
    <button type="button" className="cg-button" onClick={() => navigate('/telegram/places')}>
      Смотреть места
    </button>
    {pickerOpen ? (
      <CityPicker
        cities={cityState.cities}
        error={cityState.error}
        loading={cityState.loading}
        onClose={() => setPickerOpen(false)}
        onRetry={() => void cityState.reload()}
        onSelect={selectCity}
        selectedCity={cityState.selectedCity}
      />
    ) : null}
  </TmaShell>
}
