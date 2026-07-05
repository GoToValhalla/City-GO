import { useEffect, useState, type ReactNode } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import { getAvailableCities } from '../../api/cities/cities.api'
import { getCurrentCity, setCurrentCity, type CityOption } from '../../shared/city/currentCity'
import { ErrorState } from '../../components/ui/ErrorState'
import { Skeleton } from '../../components/ui/Skeleton'
import { isReservedCityRouteSlug } from './reservedSlugs'

type Props = { children: ReactNode }

const resolveCity = async (slug: string): Promise<CityOption | null> => {
  const current = getCurrentCity()
  if (current.slug === slug) return current
  const cities = await getAvailableCities()
  return cities.find((city) => city.slug === slug) ?? null
}

export const CityRouteScope = ({ children }: Props) => {
  const { citySlug = '' } = useParams()
  const [ready, setReady] = useState(false)
  const [missing, setMissing] = useState(false)

  useEffect(() => {
    if (!citySlug || isReservedCityRouteSlug(citySlug)) {
      setMissing(true)
      setReady(true)
      return
    }

    let active = true
    setReady(false)
    setMissing(false)

    void resolveCity(citySlug).then((city) => {
      if (!active) return
      if (!city) {
        setMissing(true)
        setReady(true)
        return
      }
      if (getCurrentCity().slug !== city.slug) setCurrentCity(city)
      setReady(true)
    }).catch(() => {
      if (!active) return
      setMissing(true)
      setReady(true)
    })

    return () => {
      active = false
    }
  }, [citySlug])

  if (isReservedCityRouteSlug(citySlug)) return <Navigate to="/" replace />
  if (!ready) return <div className="app-screen"><div className="app-container"><Skeleton /></div></div>
  if (missing) {
    return (
      <div className="app-screen">
        <div className="app-container">
          <ErrorState
            title="Город не найден"
            description="Проверьте ссылку или выберите другой город."
          />
        </div>
      </div>
    )
  }

  return <>{children}</>
}
