import { useState } from 'react'
import { PlaceMapPanel } from '../../components/places'
import { AppHeader } from '../../components/ui/AppHeader'
import { PageBreadcrumbs } from '../../components/ui/PageBreadcrumbs'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { NearbyControls } from './NearbyControls'
import { NearbyResults } from './NearbyResults'
import { useNearbySearch } from './useNearbySearch'

const RADIUS_OPTIONS = [0.1, 0.3, 1]

export const NearbyPage = () => {
  const nearby = useNearbySearch()
  const [activePlaceId, setActivePlaceId] = useState<number | null>(null)
  const user = nearby.location.snapshot?.source === 'browser'
    || nearby.location.snapshot?.source === 'telegram_native'
    ? nearby.location.snapshot.coordinates
    : null

  return <div className="app-screen"><div className="app-container">
    <AppHeader />
    <PageBreadcrumbs items={[{ label: 'Главная', to: '/' }, { label: 'Рядом' }]}
      right={<div className="places-muted">{nearby.loading ? 'Загрузка' : `${nearby.places.length} рядом`}</div>} />
    <section className="places-list-panel">
      <SectionHeader title={`Рядом: ${nearby.city.name}`}
        description="Места сортируются по расстоянию от выбранной точки. Город и радиус сохраняются при обновлении позиции." />
      <NearbyControls status={nearby.location.status} message={nearby.location.message}
        source={nearby.source} radiusKm={nearby.radiusKm} radiusOptions={RADIUS_OPTIONS}
        onRadius={nearby.setRadiusKm} onUseLocation={() => void nearby.requestLocation()}
        onUseCenter={nearby.useCenter} onOpenSettings={nearby.location.openTelegramSettings} />
      {nearby.suggestion ? <p className="nearby-city-suggestion">
        Похоже, вы ближе к городу «{nearby.suggestion.city_name}». Выбранный город не изменён.
      </p> : null}
    </section>
    <section className="places-map-list-layout">
      <PlaceMapPanel places={nearby.places} activePlaceId={activePlaceId}
        userLocation={user} manualPoint={nearby.source === 'manual' ? nearby.point : null}
        onActivePlaceChange={setActivePlaceId} onManualPoint={nearby.selectManual}
        locationError={nearby.location.status === 'insecure' ? nearby.location.message : null} />
      <NearbyResults error={nearby.error} loading={nearby.loading} places={nearby.places}
        activePlaceId={activePlaceId} onActivePlaceChange={setActivePlaceId} />
    </section>
  </div></div>
}
