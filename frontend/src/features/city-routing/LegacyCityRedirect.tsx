import { Navigate } from 'react-router-dom'
import { getCurrentCity } from '../../shared/city/currentCity'
import { cityCatalogPath, cityRouteBuildPath } from './cityPaths'

type Props = { target: 'catalog' | 'routes-build' }

export const LegacyCityRedirect = ({ target }: Props) => {
  const slug = getCurrentCity().slug
  const path = target === 'catalog' ? cityCatalogPath(slug) : cityRouteBuildPath(slug)
  return <Navigate to={path} replace />
}
