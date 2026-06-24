import { useLocationProvider } from './useLocationProvider'

export const useUserLocation = () => {
  const location = useLocationProvider()
  const coordinates = location.snapshot ? {
    lat: location.snapshot.coordinates.latitude,
    lng: location.snapshot.coordinates.longitude,
  } : null
  return {
    status: location.status,
    coordinates,
    error: location.status === 'idle' || location.status === 'granted' ? null : location.message,
    requestLocation: () => void location.request({ scenario: 'places' }),
  }
}
