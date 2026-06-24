import { useLocationProvider } from '../../../shared/location/useLocationProvider'
import type { LocationSnapshot, LocationState } from '../../../shared/location/types'

const isSnapshot = (value: LocationSnapshot | LocationState): value is LocationSnapshot =>
  'coordinates' in value

export const useRouteGeolocation = () => {
  const location = useLocationProvider()
  const requestLocation = async (): Promise<void> => {
    const result = await location.request({ scenario: 'route_navigation' })
    if (isSnapshot(result) && result.source === 'browser') location.startWatch()
  }
  const coordinates = location.snapshot?.coordinates
  return {
    status: location.status,
    position: coordinates ? {
      lat: coordinates.latitude,
      lng: coordinates.longitude,
      accuracy: coordinates.accuracy,
    } : null,
    stale: location.snapshot?.stale ?? false,
    errorMessage: location.status === 'granted' || location.status === 'idle'
      ? null
      : location.message,
    requestLocation,
    stop: location.stopWatch,
    clear: location.clear,
  }
}
